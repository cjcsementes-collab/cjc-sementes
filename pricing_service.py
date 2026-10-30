"""
Serviço de Precificação e Decisão Tributária — CAMPO vs J CASSOL
Especializado para o setor de Sementes da CJC Sementes / J Cassol Sementes Ltda. (Paraná)
Regras oficiais atualizadas:
- Vendas Internas (PR -> PR): DIFERIMENTO DE 100% no ICMS (0,0% efetivo)
- Vendas Interestaduais (PR -> Outros Estados): Redução de 60% na base do ICMS (12% -> 4,8% ou 7% -> 2,8%)
- Tributos Federais Lucro Presumido (J CASSOL):
  CSLL: 1,08%, IRPJ: 1,20%, PIS: 0,065%, COFINS: 0,30% (Total Federal = 2,645%)
- Simples Nacional (CAMPO Sementes): 3,50% fixo sobre o faturamento
- Creditação de ICMS na J CASSOL: Crédito de 4,80% nas compras interestaduais para o Paraná
"""

from icms_data import TABELA_ICMS, UFS_BRASIL, get_aliquota_icms, get_icms_venda_sementes, get_credito_compra_sementes

def calcular_decisao_tributaria(
    produto: str = "Sementes",
    quantidade: float = 1000.0,
    preco_compra_kg: float = 8.0,
    uf_origem_compra: str = "SC",
    uf_empresa_vendedora: str = "PR",
    uf_destino_venda: str = "PR",
    preco_venda_kg: float = 11.0,
    frete_total: float = 0.0,
    tipo_frete: str = "FOB",  # "FOB" ou "CIF"
    simples_pct: float = 0.035,           # 3,50% fixo CAMPO
    irpj_pct: float = 0.012,              # 1,20% J CASSOL
    csll_pct: float = 0.0108,             # 1,08% J CASSOL
    pis_pct: float = 0.00065,             # 0,065% J CASSOL
    cofins_pct: float = 0.0030,           # 0,300% J CASSOL
    reducao_base_icms_pct: float = 0.60,  # 60% de redução nas saídas interestaduais
    diferimento_interno: bool = True,     # 100% diferido nas vendas internas no PR
    credito_icms_compra_pct: float = None,# Se None, calcula pela origem (4,8% interestadual)
    margem_desejada_pct: float = None     # Se informado, calcula preço sugerido
):
    quantidade = float(quantidade or 0.0)
    preco_compra_kg = float(preco_compra_kg or 0.0)
    preco_venda_kg = float(preco_venda_kg or 0.0)
    frete_total = float(frete_total or 0.0)
    tipo_frete = (tipo_frete or "FOB").strip().upper()
    uf_origem_compra = (uf_origem_compra or "SC").strip().upper()
    uf_empresa_vendedora = (uf_empresa_vendedora or "PR").strip().upper()
    uf_destino_venda = (uf_destino_venda or "PR").strip().upper()

    # 1. Compras & Crédito de ICMS
    valor_compra = quantidade * preco_compra_kg
    
    # Determinação da alíquota de crédito de ICMS na compra
    aliq_icms_compra_tabela = get_aliquota_icms(uf_origem_compra, uf_empresa_vendedora)
    
    if credito_icms_compra_pct is not None:
        aliq_credito_compra_efetiva = float(credito_icms_compra_pct)
    else:
        # Regra de sementes: compra interestadual para o PR tem 12% na nota com redução de 60% -> crédito efetivo = 4,8%
        if uf_origem_compra != "PR":
            aliq_credito_compra_efetiva = aliq_icms_compra_tabela * (1.0 - reducao_base_icms_pct) # 12% * 40% = 4.8%
        else:
            # Compra interna dentro do PR: comumente diferida (0%), a menos que o usuário customize
            aliq_credito_compra_efetiva = 0.0

    credito_icms_compra = valor_compra * aliq_credito_compra_efetiva

    # 2. Venda & Alíquota Efetiva de ICMS da Venda de Sementes
    aliq_icms_venda_tabela = get_aliquota_icms(uf_empresa_vendedora, uf_destino_venda)
    is_venda_interna_pr = (uf_empresa_vendedora == "PR" and uf_destino_venda == "PR")

    if is_venda_interna_pr and diferimento_interno:
        # Venda interna dentro do Paraná com diferimento de 100%
        aliq_icms_venda_efetiva = 0.0
        descricao_icms_venda = "ICMS Venda (PR → PR): 0,0% (100% DIFERIDO PARA SEMENTES)"
    else:
        # Venda interestadual saindo do Paraná com redução de 60% na base
        aliq_icms_venda_efetiva = aliq_icms_venda_tabela * (1.0 - reducao_base_icms_pct)
        descricao_icms_venda = f"ICMS Venda ({uf_empresa_vendedora} → {uf_destino_venda}): {aliq_icms_venda_tabela*100:.1f}% (Efetivo c/ 60% Redução: {aliq_icms_venda_efetiva*100:.2f}%)"

    # Soma de tributos federais da J CASSOL
    federais_pct = irpj_pct + csll_pct + pis_pct + cofins_pct # 1,2% + 1,08% + 0,065% + 0,30% = 2,645%
    impostos_totais_venda_pct = aliq_icms_venda_efetiva + federais_pct # 7,445% (se 12%) ou 5,445% (se 7%) ou 2,645% (se PR)

    # Gross-up de Frete (se CIF):
    divisor_markup_frete = max(0.01, 1.0 - impostos_totais_venda_pct)
    if tipo_frete == "CIF" and frete_total > 0:
        frete_cobrado_cliente = frete_total / divisor_markup_frete
    else:
        frete_cobrado_cliente = 0.0

    valor_venda_fob = quantidade * preco_venda_kg
    valor_venda_total = valor_venda_fob + frete_cobrado_cliente
    custo_total_operacao = valor_compra + (frete_total if tipo_frete == "CIF" else 0.0)
    lucro_bruto = valor_venda_total - custo_total_operacao

    # 3. Impostos J CASSOL (Lucro Presumido)
    # Débito de ICMS da Venda
    icms_venda_debito = valor_venda_total * aliq_icms_venda_efetiva
    
    # Apuração de ICMS (Débito - Crédito)
    icms_liquido_recolher_cjc = max(0.0, icms_venda_debito - credito_icms_compra)
    saldo_credor_icms_cjc = max(0.0, credito_icms_compra - icms_venda_debito)

    # Tributos Federais J CASSOL
    irpj_cjc = valor_venda_total * irpj_pct
    csll_cjc = valor_venda_total * csll_pct
    pis_cjc = valor_venda_total * pis_pct
    cofins_cjc = valor_venda_total * cofins_pct
    total_federais_cjc = irpj_cjc + csll_cjc + pis_cjc + cofins_cjc

    # Total de impostos recolhidos em dinheiro na operação
    total_impostos_cjc = icms_liquido_recolher_cjc + total_federais_cjc
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

    # 6. Cálculo Reverso de Preço Sugerido (por margem desejada)
    sugestoes = calcular_preco_sugerido(
        quantidade=quantidade,
        preco_compra_kg=preco_compra_kg,
        frete_total=frete_total,
        tipo_frete=tipo_frete,
        margem_desejada_pct=margem_desejada_pct if margem_desejada_pct is not None else 0.20,
        aliq_credito_compra_efetiva=aliq_credito_compra_efetiva,
        aliq_icms_venda_efetiva=aliq_icms_venda_efetiva,
        simples_pct=simples_pct,
        federais_pct=federais_pct
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
        "aliq_icms_compra_tabela": aliq_icms_compra_tabela,
        "aliq_credito_compra_efetiva": aliq_credito_compra_efetiva,
        "credito_icms_compra": credito_icms_compra,
        # Tributos Venda
        "is_venda_interna_pr": is_venda_interna_pr,
        "aliq_icms_venda_tabela": aliq_icms_venda_tabela,
        "aliq_icms_venda_efetiva": aliq_icms_venda_efetiva,
        "icms_venda_debito": icms_venda_debito,
        "descricao_icms_venda": descricao_icms_venda,
        "impostos_totais_venda_pct": impostos_totais_venda_pct,
        # J CASSOL
        "icms_liquido_recolher_cjc": icms_liquido_recolher_cjc,
        "saldo_credor_icms_cjc": saldo_credor_icms_cjc,
        "irpj_cjc": irpj_cjc,
        "csll_cjc": csll_cjc,
        "pis_cjc": pis_cjc,
        "cofins_cjc": cofins_cjc,
        "total_federais_cjc": total_federais_cjc,
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
    aliq_credito_compra_efetiva: float,
    aliq_icms_venda_efetiva: float,
    simples_pct: float,
    federais_pct: float
):
    if quantidade <= 0:
        return {"preco_sugerido_campo_kg": 0.0, "preco_sugerido_j_cassol_kg": 0.0}

    frete_por_kg = (frete_total / quantidade) if (tipo_frete == "CIF" and frete_total > 0) else 0.0
    custo_base_kg = preco_compra_kg + frete_por_kg
    credito_kg = preco_compra_kg * aliq_credito_compra_efetiva

    # 1. Sugestão CAMPO (Simples Nacional)
    divisor_campo = 1.0 - simples_pct - margem_desejada_pct
    preco_campo_kg = (custo_base_kg / divisor_campo) if divisor_campo > 0 else 0.0

    # 2. Sugestão J CASSOL (Lucro Presumido)
    # Hipótese A: Crédito cobre o débito (ex.: venda interna PR onde débito é 0, ou venda interestadual com crédito abundante)
    divisor_sem_icms = 1.0 - federais_pct - margem_desejada_pct
    preco_j_cassol_hipA = (custo_base_kg / divisor_sem_icms) if divisor_sem_icms > 0 else 0.0
    debito_icms_hipA = preco_j_cassol_hipA * aliq_icms_venda_efetiva

    if credito_kg >= debito_icms_hipA:
        preco_j_cassol_kg = preco_j_cassol_hipA
    else:
        # Hipótese B: Débito supera o crédito
        divisor_com_icms = 1.0 - federais_pct - aliq_icms_venda_efetiva - margem_desejada_pct
        preco_j_cassol_kg = ((custo_base_kg - credito_kg) / divisor_com_icms) if divisor_com_icms > 0 else 0.0

    return {
        "preco_sugerido_campo_kg": round(preco_campo_kg, 4),
        "preco_sugerido_campo_total": round(preco_campo_kg * quantidade, 2),
        "preco_sugerido_j_cassol_kg": round(preco_j_cassol_kg, 4),
        "preco_sugerido_j_cassol_total": round(preco_j_cassol_kg * quantidade, 2),
        "margem_desejada_pct": margem_desejada_pct
    }
