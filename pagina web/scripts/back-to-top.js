/**
 * Botón "volver arriba" para OIB Sleep
 * Muestra un botón elegante cuando el usuario hace scroll
 */

document.addEventListener('DOMContentLoaded', function() {
    // Crear el botón y añadirlo al DOM
    createBackToTopButton();
    
    // Función para manejar la visibilidad del botón
    function handleScroll() {
        const backToTopButton = document.querySelector('.back-to-top');
        
        // Si el usuario ha desplazado más de 300px, mostrar el botón
        if (window.scrollY > 300) {
            backToTopButton.classList.add('visible');
        } else {
            backToTopButton.classList.remove('visible');
        }
    }
    
    // Escuchar eventos de scroll
    window.addEventListener('scroll', handleScroll);
});

/**
 * Crea el botón de "volver arriba" y lo añade al documento
 */
function createBackToTopButton() {
    // Comprobar si el botón ya existe
    if (document.querySelector('.back-to-top')) {
        return;
    }
    
    // Crear elemento de botón
    const backToTopButton = document.createElement('button');
    backToTopButton.className = 'back-to-top';
    backToTopButton.setAttribute('aria-label', 'Volver arriba');
    backToTopButton.innerHTML = '&#9650;'; // Símbolo de flecha hacia arriba
    
    // Añadir el botón al final del body
    document.body.appendChild(backToTopButton);
    
    // Añadir funcionalidad de scroll suave al hacer clic
    backToTopButton.addEventListener('click', function() {
        // Usar scrollTo con animación suave
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}
