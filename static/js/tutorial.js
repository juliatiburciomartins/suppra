document.addEventListener("DOMContentLoaded", () => {
    let currentStep = 1;
    const totalSteps = 3;

    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const stepIndicator = document.getElementById('stepIndicator');
    const tutorialForm = document.getElementById('tutorialForm');

    function showStep(step) {
        document.querySelectorAll('.onboarding-step').forEach(el => {
            el.classList.remove('active');
        });
        
        const target = document.querySelector(`[data-step="${step}"]`);
        if (target) {
            target.classList.add('active');
        }

        if (prevBtn) prevBtn.disabled = step === 1;
        if (stepIndicator) stepIndicator.textContent = `${step} de ${totalSteps}`;
        
        if (nextBtn) {
            if (step === totalSteps) {
                nextBtn.textContent = 'Concluir';
                nextBtn.onclick = function() {
                    if (tutorialForm) tutorialForm.submit();
                };
            } else {
                nextBtn.textContent = 'Próximo';
                nextBtn.onclick = nextStep;
            }
        }
    }

    function nextStep() {
        if (currentStep < totalSteps) {
            currentStep++;
            showStep(currentStep);
        }
    }

    function prevStep() {
        if (currentStep > 1) {
            currentStep--;
            showStep(currentStep);
        }
    }

    // ISSO É O MAIS IMPORTANTE PARA ARQUIVOS SEPARADOS:
    // Expõe as funções para o navegador enxergar o onclick do HTML
    window.nextStep = nextStep;
    window.prevStep = prevStep;

    showStep(1);
});