// page-transition.js - Efecto de pasar página adaptativo para móvil y escritorio

// Variables para la animación de transición
let isAnimating = false;
const transitionDuration = 800; // Duración de la transición en ms
const transitionOverlay = document.createElement('div');
const pageElement = document.createElement('div');

// Configuración inicial de los elementos de transición
function setupTransitionElements() {
  // Contenedor principal
  transitionOverlay.className = 'page-transition-overlay';
  transitionOverlay.style.position = 'fixed';
  transitionOverlay.style.top = '0';
  transitionOverlay.style.left = '0';
  transitionOverlay.style.width = '100%';
  transitionOverlay.style.height = '100%';
  transitionOverlay.style.zIndex = '9999';
  transitionOverlay.style.visibility = 'hidden';
  transitionOverlay.style.overflow = 'hidden';
  transitionOverlay.style.pointerEvents = 'none';
  document.body.appendChild(transitionOverlay);
  
  // Elemento que simula la página - Cambiado a usar el color del fondo de la página
  pageElement.className = 'page-flip-element';
  pageElement.style.position = 'absolute';
  pageElement.style.width = '100%';
  pageElement.style.height = '100%';
  
  // Usar el mismo color y gradiente que el fondo de la página
  pageElement.style.backgroundColor = '#0d1b21';
  pageElement.style.transition = `transform ${transitionDuration/1000}s cubic-bezier(0.645, 0.045, 0.355, 1.000)`;
  pageElement.style.transformOrigin = 'left center';
  transitionOverlay.appendChild(pageElement);
  
  // Posicionar según el dispositivo
  positionPageElement();
  
  // Añadir gradiente igual al del body::before
  const gradientOverlay = document.createElement('div');
  gradientOverlay.style.position = 'absolute';
  gradientOverlay.style.top = '0';
  gradientOverlay.style.left = '0';
  gradientOverlay.style.width = '100%';
  gradientOverlay.style.height = '100%';
  gradientOverlay.style.background = 'linear-gradient(135deg, rgba(13, 27, 33, 0.85) 0%, rgba(30, 58, 138, 0.75) 100%)';
  gradientOverlay.style.zIndex = '1';
  pageElement.appendChild(gradientOverlay);
}

// Ajustar posición según el dispositivo (móvil o escritorio)
function positionPageElement() {
  const isMobile = window.innerWidth <= 768;
  
  if (isMobile) {
    // En móvil: transición vertical (de arriba a abajo)
    pageElement.style.top = '-100%';
    pageElement.style.right = '0';
    pageElement.style.left = '0';
    pageElement.style.transform = 'translateY(0)';
    pageElement.style.transformOrigin = 'center top';
    pageElement.style.backgroundImage = 'linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)';
    pageElement.style.boxShadow = '0 5px 15px rgba(0,0,0,0.3)';
  } else {
    // En escritorio: transición horizontal (derecha a izquierda)
    pageElement.style.top = '0';
    pageElement.style.right = '-100%';
    pageElement.style.left = 'auto';
    pageElement.style.transform = 'translateX(0)';
    pageElement.style.transformOrigin = 'left center';
    pageElement.style.backgroundImage = 'linear-gradient(to left, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)';
    pageElement.style.boxShadow = '-5px 0 15px rgba(0,0,0,0.3)';
  }
}

// Iniciar la transición antes de cambiar de página
function startTransition(url, direction) {
  if (isAnimating) return;
  isAnimating = true;
  
  const isMobile = window.innerWidth <= 768;
  
  // Mostrar la capa de transición
  transitionOverlay.style.visibility = 'visible';
  
  setTimeout(() => {
    if (isMobile) {
      // Transición móvil: vertical
      if (direction === 'up') {
        // Hacia arriba
        pageElement.style.top = '0';
        pageElement.style.transform = 'translateY(-100%)';
      } else {
        // Hacia abajo (por defecto)
        pageElement.style.top = '-100%';
        pageElement.style.transform = 'translateY(100%)';
      }
    } else {
      // Transición escritorio: horizontal
      if (direction === 'left') {
        // De izquierda a derecha
        pageElement.style.left = '-100%';
        pageElement.style.right = 'auto';
        pageElement.style.transform = 'translateX(100%)';
      } else {
        // De derecha a izquierda (por defecto)
        pageElement.style.right = '100%';
        pageElement.style.left = 'auto';
        pageElement.style.transform = 'translateX(100%)';
      }
    }
    
    // Esperar a que termine la animación y luego navegar a la nueva página
    setTimeout(() => {
      window.location.href = url;
    }, transitionDuration - 50);
  }, 50);
}

// Manejar la animación cuando la página carga
function handlePageLoad() {
  if (transitionOverlay) {
    const isMobile = window.innerWidth <= 768;
    
    // Si venimos de otra página, configurar para salida
    transitionOverlay.style.visibility = 'visible';
    
    if (isMobile) {
      // Configurar salida para móvil
      pageElement.style.top = '0';
      pageElement.style.transform = 'translateY(0)';
      
      setTimeout(() => {
        // Animar la página saliendo hacia arriba
        pageElement.style.transform = 'translateY(-100%)';
        
        setTimeout(() => {
          transitionOverlay.style.visibility = 'hidden';
          isAnimating = false;
        }, transitionDuration);
      }, 100);
    } else {
      // Configurar salida para escritorio
      pageElement.style.right = 'auto';
      pageElement.style.left = '0';
      pageElement.style.transform = 'translateX(0)';
      
      setTimeout(() => {
        // Animar la página saliendo hacia la izquierda
        pageElement.style.transform = 'translateX(-100%)';
        
        setTimeout(() => {
          transitionOverlay.style.visibility = 'hidden';
          isAnimating = false;
        }, transitionDuration);
      }, 100);
    }
  }
}

// Detectar dirección de navegación
function determineDirection(targetUrl) {
  // Lista ordenada de páginas para determinar dirección
  const pageOrder = [
    'index.html', 
    'Sobre-nosotros.html', 
    'galería.html', 
    'Contacto.html'
  ];
  
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  const targetPage = targetUrl.split('/').pop();
  
  const currentIndex = pageOrder.indexOf(currentPage);
  const targetIndex = pageOrder.indexOf(targetPage);
  
  // Si no podemos determinar, usar dirección por defecto
  if (currentIndex === -1 || targetIndex === -1) return 'left';
  
  return targetIndex > currentIndex ? 'right' : 'left';
}

// Manejar redimensionamiento de la ventana
function handleResize() {
  positionPageElement();
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  setupTransitionElements();
  handlePageLoad();
  
  // Manejar cambio de tamaño de ventana
  window.addEventListener('resize', handleResize);
  
  // Capturar todos los enlaces internos para aplicar la transición
  document.querySelectorAll('a').forEach(link => {
    // Solo aplicar a enlaces internos (mismo dominio)
    if (link.hostname === window.location.hostname) {
      link.addEventListener('click', function(e) {
        const url = this.getAttribute('href');
        
        // No hacer la transición si es la misma página o es un ancla
        if (url === '#' || url.startsWith('#') || url === window.location.pathname) {
          return;
        }
        
        e.preventDefault();
        const direction = determineDirection(url);
        startTransition(url, direction);
      });
    }
  });
});

// Agregar estilos adicionales para mejorar la experiencia
const transitionStyles = document.createElement('style');
transitionStyles.textContent = `
  body {
    overflow-x: hidden;
  }
  
  /* Animación para el contenido de la página */
  main {
    animation: fadeIn 0.5s ease-out 0.3s both;
  }
  
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  
  /* Agregar línea de pliegue (adaptativa) */
  @media (min-width: 769px) {
    .page-flip-element::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 2px;
      height: 100%;
      background: linear-gradient(to right, rgba(0,0,0,0.2), rgba(0,0,0,0));
    }
  }
  
  @media (max-width: 768px) {
    .page-flip-element::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 2px;
      background: linear-gradient(to bottom, rgba(0,0,0,0.2), rgba(0,0,0,0));
    }
  }
`;
document.head.appendChild(transitionStyles);