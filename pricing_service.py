"""
Serviço de Precificação e Decisão Tributária — CAMPO vs J CASSOL
Desenvolvido especificamente para a CJC Sementes / J Cassol Sementes Ltda.
Espelha com 100% de fidelidade a planilha de decisão tributária, matriz de ICMS 2026,
redução de base de cálculo do ICMS, créditos de compra e gross-up de frete.
"""

from icms_data import TABELA_ICMS, UFS_BRASIL, get_aliquota_icms

def calcular_decisao_tributaria(
    produto: str = "Trigo Mourisco",
    quantidade: float = 25000.0,
    preco_compra_kg: float = 2.0,
    uf_origem_compra: str = "MG",
    uf_empresa_vendedora: str = "PR",
    uf_destino_venda: str = "MS",
    preco_venda_kg: float = 2.65,
    frete_total: float = 0.0,
    tipo_frete: str = "FOB",  # "FOB" ou "CIF"
    simples_pct: float = 0.035,
    irpj_pct: float = 0.012,
    csll_pct: float = 0.0108,
    reducao_base_icms_pct: float = 0.60,
    credito_icms_utilizavel_pct: float = 1.0,  # 100% ou 40% (manutenção proporcional)
    pis_cofins_incide: bool = False,
    pis_cofins_pct: float = 0.0365,
    margem_desejada_pct: float = None  # Se informado, calcula o preço sugerido
):
    quantidade = float(quantidade or 0.0)
    preco_compra_kg = float(preco_compra_kg or 0.0)
    preco_venda_kg = float(preco_venda_kg or 0.0)
    frete_total = float(frete_total or 0.0)
    tipo_frete = (tipo_frete or "FOB").strip().upper()

    # 1. Compras
    valor_compra = quantidade * preco_compra_kg
    aliq_icms_compra = get_aliquota_icms(uf_origem_compra, uf_empresa_vendedora)
    
    # Redução de base de cálculo (ex.: 60% de redução -> base efetiva 40%)
    base_efetiva = max(0.0, 1.0 - reducao_base_icms_pct)
    aliq_icms_compra_efetiva = aliq_icms_compra * base_efetiva
    
    icms_compra_destacado = valor_compra * aliq_icms_compra_efetiva
    credito_icms_utilizavel = icms_compra_destacado * credito_icms_utilizavel_pct

    # 2. Venda & Alíquota Interestadual da Venda
    aliq_icms_venda = get_aliquota_icms(uf_empresa_vendedora, uf_destino_venda)
    aliq_icms_venda_efetiva = aliq_icms_venda * base_efetiva

    # Gross-up de Frete (se CIF):
    # O frete cobrado do cliente embutido na nota de venda sofre ICMS + IRPJ + CSLL (+ PIS/COFINS)
    impostos_frete_pct = aliq_icms_venda_efetiva + irpj_pct + csll_pct + (pis_cofins_pct if pis_cofins_incide else 0.0)
    divisor_markup_frete = max(0.01, 1.0 - impostos_frete_pct)
    
    if tipo_frete == "CIF" and frete_total > 0:
        frete_cobrado_cliente = frete_total / divisor_markup_frete
    else:
        frete_cobrado_cliente = 0.0

    valor_venda_fob = quantidade * preco_venda_kg
    valor_venda_total = valor_venda_fob + frete_cobrado_cliente
    custo_total_operacao = valor_compra + (frete_total if tipo_frete == "CIF" else 0.0)
    lucro_bruto = valor_venda_total - custo_total_operacao

    # 3. Impostos J CASSOL (Lucro Presumido)
    icms_venda_efetivo = valor_venda_total * aliq_icms_venda_efetiva
    icms_liquido_recolher_cjc = max(0.0, icms_venda_efetivo - credito_icms_utilizavel)
    saldo_credor_icms_cjc = max(0.0, credito_icms_utilizavel - icms_venda_efetivo)

    irpj_cjc = valor_venda_total * irpj_pct
    csll_cjc = valor_venda_total * csll_pct
    pis_cofins_cjc = (valor_venda_total * pis_cofins_pct) if pis_cofins_incide else 0.0

    total_impostos_cjc = icms_liquido_recolher_cjc + irpj_cjc + csll_cjc + pis_cofins_cjc
    resultado_liquido_cjc = lucro_bruto - total_impostos_cjc
    custo_tributario_cjc_pct = (total_impostos_cjc / valor_venda_total) if valor_venda_total > 0 else 0.0
    margem_liquida_cjc_pct = (resultado_liquido_cjc / valor_venda_total) if valor_venda_total > 0 else 0.0

    # 4. Impostos CAMPO (Simples Nacional)
    total_impostos_campo = valor_venda_total * simples_pct
    resultado_liquido_campo = lucro_bruto - total_impostos_campo
    custo_tributario_campo_pct = simples_pct
    margem_liquida_campo_pct = (resultado_liquido_campo / valor_venda_total) if valor_venda_total > 0 else 0.0

    # 5. Veredito Comparativo
    diff = resultado_liquido_cjc - resultado_liquido_campo
    if diff > 0.001:
        melhor_empresa = "J CASSOL (Lucro Presumido)"
        empresa_codigo = "JCASSOL"
        vantagem_reais = diff
    elif diff < -0.001:
        melhor_empresa = "CAMPO (Simples Nacional)"
        empresa_codigo = "CAMPO"
        vantagem_reais = abs(diff)
    else:
        melhor_empresa = "EMPATE (Indiferente)"
        empresa_codigo = "EMPATE"
        vantagem_reais = 0.0

    vantagem_pct_venda = (vantagem_reais / valor_venda_total) if valor_venda_total > 0 else 0.0

    # 6. Cálculo Reverso de Preço Sugerido (se margem desejada foi fornecida ou para sugestão)
    sugestoes = calcular_preco_sugerido(
        quantidade=quantidade,
        preco_compra_kg=preco_compra_kg,
        frete_total=frete_total,
        tipo_frete=tipo_frete,
        margem_desejada_pct=margem_desejada_pct if margem_desejada_pct is not None else 0.20,
        uf_origem_compra=uf_origem_compra,
        uf_empresa_vendedora=uf_empresa_vendedora,
        uf_destino_venda=uf_destino_venda,
        simples_pct=simples_pct,
        irpj_pct=irpj_pct,
        csll_pct=csll_pct,
        reducao_base_icms_pct=reducao_base_icms_pct,
        credito_icms_utilizavel_pct=credito_icms_utilizavel_pct,
        pis_cofins_incide=pis_cofins_incide,
        pis_cofins_pct=pis_cofins_pct
    )

    return {
        "produto": produto,
        "quantidade": quantidade,
        "preco_compra_kg": preco_compra_kg,
        "uf_origem_compra": uf_origem_compra,
        "uf_empresa_vendedora": uf_empresa_vendedora,
        "uf_destino_venda": uf_destino_venda,
        "preco_venda_kg": preco_venda_kg,
        "frete_total": frete_total,
        "tipo_frete": tipo_frete,
        "frete_cobrado_cliente": frete_cobrado_cliente,
        "divisor_markup_frete": divisor_markup_frete,
        "valor_compra": valor_compra,
        "valor_venda_fob": valor_venda_fob,
        "valor_venda_total": valor_venda_total,
        "custo_total_operacao": custo_total_operacao,
        "lucro_bruto": lucro_bruto,
        # Tributos Compra
        "aliq_icms_compra": aliq_icms_compra,
        "aliq_icms_compra_efetiva": aliq_icms_compra_efetiva,
        "icms_compra_destacado": icms_compra_destacado,
        "credito_icms_utilizavel": credito_icms_utilizavel,
        # Tributos Venda
        "aliq_icms_venda": aliq_icms_venda,
        "aliq_icms_venda_efetiva": aliq_icms_venda_efetiva,
        "icms_venda_efetivo": icms_venda_efetivo,
        # J CASSOL
        "icms_liquido_recolher_cjc": icms_liquido_recolher_cjc,
        "saldo_credor_icms_cjc": saldo_credor_icms_cjc,
        "irpj_cjc": irpj_cjc,
        "csll_cjc": csll_cjc,
        "pis_cofins_cjc": pis_cofins_cjc,
        "total_impostos_cjc": total_impostos_cjc,
        "resultado_liquido_cjc": resultado_liquido_cjc,
        "custo_tributario_cjc_pct": custo_tributario_cjc_pct,
        "margem_liquida_cjc_pct": margem_liquida_cjc_pct,
        # CAMPO
        "total_impostos_campo": total_impostos_campo,
        "resultado_liquido_campo": resultado_liquido_campo,
        "custo_tributario_campo_pct": custo_tributario_campo_pct,
        "margem_liquida_campo_pct": margem_liquida_campo_pct,
        # Veredito
        "melhor_empresa": melhor_empresa,
        "empresa_codigo": empresa_codigo,
        "vantagem_reais": vantagem_reais,
        "vantagem_pct_venda": vantagem_pct_venda,
        # Sugestões
        "sugestoes_preco": sugestoes
    }


def calcular_preco_sugerido(
    quantidade: float,
    preco_compra_kg: float,
    frete_total: float,
    tipo_frete: str,
    margem_desejada_pct: float,
    uf_origem_compra: str,
    uf_empresa_vendedora: str,
    uf_destino_venda: str,
    simples_pct: float,
    irpj_pct: float,
    csll_pct: float,
    reducao_base_icms_pct: float,
    credito_icms_utilizavel_pct: float,
    pis_cofins_incide: bool,
    pis_cofins_pct: float
):
    if quantidade <= 0:
        return {"preco_sugerido_campo_kg": 0.0, "preco_sugerido_j_cassol_kg": 0.0}

    # Custo da mercadoria por kg (se frete CIF, adicionamos frete_total / quantidade)
    frete_por_kg = (frete_total / quantidade) if (tipo_frete == "CIF" and frete_total > 0) else 0.0
    custo_base_kg = preco_compra_kg + frete_por_kg
    base_efetiva = max(0.0, 1.0 - reducao_base_icms_pct)

    # 1. Sugestão CAMPO (Simples Nacional)
    # Preço * (1 - Simples - Margem) = Custo
    divisor_campo = 1.0 - simples_pct - margem_desejada_pct
    preco_campo_kg = (custo_base_kg / divisor_campo) if divisor_campo > 0 else 0.0

    # 2. Sugestão J CASSOL (Lucro Presumido)
    aliq_compra = get_aliquota_icms(uf_origem_compra, uf_empresa_vendedora)
    credito_icms_kg = preco_compra_kg * aliq_compra * base_efetiva * credito_icms_utilizavel_pct

    aliq_venda = get_aliquota_icms(uf_empresa_vendedora, uf_destino_venda)
    aliq_venda_efetiva = aliq_venda * base_efetiva

    impostos_federais = irpj_pct + csll_pct + (pis_cofins_pct if pis_cofins_incide else 0.0)

    # Hipótese A: Crédito de ICMS cobre o débito da venda (ICMS a recolher = 0)
    divisor_sem_icms = 1.0 - impostos_federais - margem_desejada_pct
    preco_j_cassol_hipA = (custo_base_kg / divisor_sem_icms) if divisor_sem_icms > 0 else 0.0
    debito_icms_hipA = preco_j_cassol_hipA * aliq_venda_efetiva

    if credito_icms_kg >= debito_icms_hipA:
        preco_j_cassol_kg = preco_j_cassol_hipA
    else:
        # Hipótese B: Débito de ICMS supera o crédito
        divisor_com_icms = 1.0 - impostos_federais - aliq_venda_efetiva - margem_desejada_pct
        preco_j_cassol_kg = ((custo_base_kg - credito_icms_kg) / divisor_com_icms) if divisor_com_icms > 0 else 0.0

    return {
        "preco_sugerido_campo_kg": round(preco_campo_kg, 4),
        "preco_sugerido_campo_total": round(preco_campo_kg * quantidade, 2),
        "preco_sugerido_j_cassol_kg": round(preco_j_cassol_kg, 4),
        "preco_sugerido_j_cassol_total": round(preco_j_cassol_kg * quantidade, 2),
        "margem_desejada_pct": margem_desejada_pct
    }
