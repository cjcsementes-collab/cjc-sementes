document.addEventListener('DOMContentLoaded', function() {

    // Mobile Menu Toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', function() {
            this.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                mobileMenuBtn.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });
    }

    
    // 1. Fechamento de Mensagens de Alerta (Flash)
    const alertCloses = document.querySelectorAll('.alert-close');
    alertCloses.forEach(btn => {
        btn.addEventListener('click', function() {
            const alert = this.parentElement;
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    });

    // 2. Seletor de Quantidade na Página de Detalhes do Produto
    const qtyInput = document.getElementById('quantidade-selector');
    const btnMinus = document.getElementById('qty-minus');
    const btnPlus = document.getElementById('qty-plus');
    const priceElement = document.getElementById('product-base-price');
    const totalDetailPrice = document.getElementById('product-total-price');

    if (qtyInput && priceElement && totalDetailPrice) {
        const basePrice = parseFloat(priceElement.getAttribute('data-price'));
        
        function updateDetailTotal() {
            let qty = parseFloat(qtyInput.value);
            if (isNaN(qty) || qty <= 0) qty = 1;
            const total = basePrice * qty;
            totalDetailPrice.innerText = total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        }

        if (btnMinus) {
            btnMinus.addEventListener('click', () => {
                let current = parseFloat(qtyInput.value);
                if (current > 1) {
                    qtyInput.value = current - 1;
                    updateDetailTotal();
                }
            });
        }

        if (btnPlus) {
            btnPlus.addEventListener('click', () => {
                let current = parseFloat(qtyInput.value);
                qtyInput.value = current + 1;
                updateDetailTotal();
            });
        }

        qtyInput.addEventListener('input', updateDetailTotal);
    }

    // 3. Simulador de Frete no Carrinho
    const btnCalcShipping = document.getElementById('btn-calc-shipping');
    const inputCep = document.getElementById('cep-input');
    const shippingResults = document.getElementById('shipping-options-wrapper');
    const totalWeightKg = parseFloat(document.getElementById('cart-total-weight')?.value || 0);

    if (btnCalcShipping && inputCep && shippingResults) {
        btnCalcShipping.addEventListener('click', function() {
            const cep = inputCep.value.trim();
            if (cep.replace('-', '').length !== 8) {
                alert('Por favor, informe um CEP válido com 8 dígitos.');
                return;
            }

            btnCalcShipping.innerText = 'Calculando...';
            btnCalcShipping.disabled = true;

            const formData = new FormData();
            formData.append('cep', cep);
            formData.append('peso', totalWeightKg);

            fetch('/carrinho/calcular-frete', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao calcular frete');
                }
                return response.json();
            })
            .then(data => {
                btnCalcShipping.innerText = 'Calcular';
                btnCalcShipping.disabled = false;
                shippingResults.innerHTML = '';

                if (data.opcoes && data.opcoes.length > 0) {
                    data.opcoes.forEach((opcao, idx) => {
                        const optElement = document.createElement('div');
                        optElement.className = 'shipping-option-label';
                        optElement.innerHTML = `
                            <div>
                                <strong>${opcao.nome}</strong><br>
                                <small>${opcao.prazo}</small>
                            </div>
                            <strong style="color: var(--verde-safra)">
                                ${opcao.valor === 0 ? 'Grátis' : opcao.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                            </strong>
                        `;
                        shippingResults.appendChild(optElement);
                    });
                }
            })
            .catch(err => {
                console.error(err);
                btnCalcShipping.innerText = 'Calcular';
                btnCalcShipping.disabled = false;
                shippingResults.innerHTML = '<div style="color:red; font-size: 0.8rem;">Erro ao calcular frete. Verifique o CEP.</div>';
            });
        });
    }

    // 4. Alternador de Formas de Pagamento e Seleção de Frete no Checkout
    const paymentPix = document.getElementById('payment-pix');
    const paymentCard = document.getElementById('payment-card');
    const pixBox = document.getElementById('pix-info-box');
    const cardBox = document.getElementById('card-info-box');
    const inputMetodo = document.getElementById('input-metodo-pagamento');

    if (paymentPix && paymentCard && pixBox && cardBox && inputMetodo) {
        paymentPix.addEventListener('click', () => {
            paymentPix.classList.add('selected');
            paymentCard.classList.remove('selected');
            pixBox.style.display = 'block';
            cardBox.style.display = 'none';
            inputMetodo.value = 'PIX';
        });

        paymentCard.addEventListener('click', () => {
            paymentCard.classList.add('selected');
            paymentPix.classList.remove('selected');
            cardBox.style.display = 'block';
            pixBox.style.display = 'none';
            inputMetodo.value = 'Cartão';
        });
    }

    // Lógica para carregar opções de frete na tela de checkout e recalcular o total final
    const checkoutCep = document.getElementById('checkout-cep');
    const checkoutWeight = parseFloat(document.getElementById('checkout-total-weight')?.value || 0);
    const checkoutShippingOpts = document.getElementById('checkout-shipping-options');
    const checkoutSubtotal = parseFloat(document.getElementById('checkout-subtotal-val')?.value || 0);
    
    const labelFreteText = document.getElementById('text-valor-frete');
    const labelTotalText = document.getElementById('text-valor-total');
    const inputValorFrete = document.getElementById('input-valor-frete');
    const inputFreteOpcao = document.getElementById('input-frete-opcao');

    if (checkoutCep && checkoutShippingOpts) {
        checkoutCep.addEventListener('blur', function() {
            const cep = checkoutCep.value.trim().replace('-', '');
            if (cep.length !== 8) return;

            checkoutShippingOpts.innerHTML = '<p style="font-size:0.85rem; color:var(--text-muted)">Buscando transportadoras parceiras...</p>';

            const formData = new FormData();
            formData.append('cep', cep);
            formData.append('peso', checkoutWeight);

            fetch('/carrinho/calcular-frete', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                checkoutShippingOpts.innerHTML = '';
                if (data.opcoes) {
                    data.opcoes.forEach((opcao, idx) => {
                        const div = document.createElement('div');
                        div.className = `shipping-option-label ${idx === 0 ? 'selected' : ''}`;
                        div.setAttribute('data-valor', opcao.valor);
                        div.setAttribute('data-nome', opcao.nome);
                        div.innerHTML = `
                            <div>
                                <input type="radio" name="temp_frete" id="opt_${idx}" ${idx === 0 ? 'checked' : ''} style="margin-right:8px">
                                <strong>${opcao.nome}</strong><br>
                                <small style="margin-left: 20px">${opcao.prazo}</small>
                            </div>
                            <strong style="color: var(--verde-safra)">
                                ${opcao.valor === 0 ? 'Grátis' : opcao.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                            </strong>
                        `;
                        
                        // Clique no card seleciona o radio button
                        div.addEventListener('click', function() {
                            document.querySelectorAll('.shipping-option-label').forEach(el => el.classList.remove('selected'));
                            this.classList.add('selected');
                            const radio = this.querySelector('input[type="radio"]');
                            if (radio) radio.checked = true;
                            
                            // Atualiza valores globais
                            updateFinalTotal(opcao.valor, opcao.nome);
                        });
                        
                        checkoutShippingOpts.appendChild(div);
                    });

                    // Define o padrão inicial
                    if (data.opcoes.length > 0) {
                        updateFinalTotal(data.opcoes[0].valor, data.opcoes[0].nome);
                    }
                }
            })
            .catch(err => {
                console.error(err);
                checkoutShippingOpts.innerHTML = '<p style="color:red; font-size:0.85rem">Erro ao buscar transportadoras.</p>';
            });
        });
    }

    function updateFinalTotal(valorFrete, nomeFrete) {
        if (labelFreteText && labelTotalText && inputValorFrete && inputFreteOpcao) {
            inputValorFrete.value = valorFrete;
            inputFreteOpcao.value = nomeFrete;
            
            labelFreteText.innerText = valorFrete === 0 ? 'Grátis' : valorFrete.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            
            const total = checkoutSubtotal + valorFrete;
            labelTotalText.innerText = total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        }
    }

    // 5. Máscaras e Validações Simples nos Inputs de Formulário
    const cpfInput = document.querySelector('input[placeholder="000.000.000-00"]');
    if (cpfInput) {
        cpfInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, "");
            if (value.length > 11) value = value.slice(0, 11);
            
            // Aplica máscara
            if (value.length > 9) {
                value = value.replace(/^(\d{3})(\d{3})(\d{3})(\d{1,2})$/, "$1.$2.$3-$4");
            } else if (value.length > 6) {
                value = value.replace(/^(\d{3})(\d{3})(\d{1,3})$/, "$1.$2.$3");
            } else if (value.length > 3) {
                value = value.replace(/^(\d{3})(\d{1,3})$/, "$1.$2");
            }
            e.target.value = value;
        });
    }

    const telInput = document.querySelector('input[placeholder="(00) 00000-0000"]');
    if (telInput) {
        telInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, "");
            if (value.length > 11) value = value.slice(0, 11);
            
            if (value.length > 6) {
                value = value.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
            } else if (value.length > 2) {
                value = value.replace(/^(\d{2})(\d{1,5})$/, "($1) $2");
            }
            e.target.value = value;
        });
    }

    const cepInputMask = document.querySelectorAll('input[placeholder="00000-000"]');
    cepInputMask.forEach(cep => {
        cep.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, "");
            if (value.length > 8) value = value.slice(0, 8);
            if (value.length > 5) {
                value = value.replace(/^(\d{5})(\d{1,3})$/, "$1-$2");
            }
            e.target.value = value;
        });
    });
    
    // Copiar código Pix Copia e Cola
    const btnCopyPix = document.getElementById('btn-copiar-pix');
    const textareaPix = document.getElementById('pix-copia-cola-text');
    if (btnCopyPix && textareaPix) {
        btnCopyPix.addEventListener('click', function() {
            textareaPix.select();
            document.execCommand('copy');
            btnCopyPix.innerText = 'Copiado!';
            btnCopyPix.style.backgroundColor = 'var(--verde-safra)';
            setTimeout(() => {
                btnCopyPix.innerText = 'Copiar Código';
                btnCopyPix.style.backgroundColor = 'var(--laranja-brasa)';
            }, 2000);
        });
    }
});
