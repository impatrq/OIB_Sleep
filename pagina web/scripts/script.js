function toggleMenu() {
    const navLinks = document.querySelector('.nav-links');
    navLinks.classList.toggle('active');
}

document.addEventListener('DOMContentLoaded', function () {
    // Inicializar las animaciones al hacer scroll
    initScrollReveal();

    // Añadir comportamiento para ocultar/mostrar header al hacer scroll
    initHeaderScrollEffect();

    const modelViewer = document.querySelector('#bed-model');

    if (!modelViewer) return;

    // Detectar si es un dispositivo móvil
    const isMobile = window.innerWidth <= 768;
    
    // Control de medidas con botón
    const toggleDimensionsButton = document.getElementById('toggle-dimensions');
    const dimElements = [...modelViewer.querySelectorAll('.dim')];
    const dimensionLines = modelViewer.querySelector('#dimLines');
    let dimensionsVisible = false;
    let wasAutoRotating = false;
    let dimensionUpdateInterval = null;
    
    // Función para mostrar/ocultar las dimensiones
    function toggleDimensions() {
        dimensionsVisible = !dimensionsVisible;
        
        if (dimensionsVisible) {
            // Guardar el estado actual de rotación
            wasAutoRotating = modelViewer.hasAttribute('auto-rotate');
            
            // Detener la rotación si está activa
            if (wasAutoRotating) {
                modelViewer.removeAttribute('auto-rotate');
            }
            
            // Desactivar controles de cámara y otras interacciones
            modelViewer.removeAttribute('camera-controls');
            modelViewer.setAttribute('disable-tap', '');
            modelViewer.setAttribute('disable-zoom', '');
            modelViewer.setAttribute('disable-pan', '');
            
            modelViewer.classList.add('dimensions-visible');
            toggleDimensionsButton.classList.add('active');
            
            // Mostrar el control de unidades
            const controlsElement = modelViewer.querySelector('#controls');
            if (controlsElement) {
                controlsElement.classList.remove('hide');
            }
            
            // Asegurarse de que todas las líneas estén visibles inmediatamente
            const allDimLines = modelViewer.querySelectorAll('.dimensionLine');
            allDimLines.forEach(line => {
                line.classList.remove('hide');
            });
            
            // La visibilidad de las etiquetas se maneja en updateDimensionVisibility
            updateDimensionVisibility();
            
            // Renderizar inmediatamente el SVG y establecer un intervalo para actualizaciones frecuentes
            renderSVG();
            if (dimensionUpdateInterval) clearInterval(dimensionUpdateInterval);
            dimensionUpdateInterval = setInterval(renderSVG, 100); // Actualizar cada 100ms
        } else {
            // Restaurar interacciones
            modelViewer.setAttribute('camera-controls', '');
            modelViewer.removeAttribute('disable-tap');
            
            // Mantener el zoom deshabilitado independientemente de si estamos en móvil o no
            modelViewer.setAttribute('disable-zoom', '');
            
            // Restaurar la rotación automática si estaba activa antes
            if (wasAutoRotating) {
                modelViewer.setAttribute('auto-rotate', '');
            }
            
            modelViewer.classList.remove('dimensions-visible');
            toggleDimensionsButton.classList.remove('active');
            
            // Ocultar el control de unidades
            const controlsElement = modelViewer.querySelector('#controls');
            if (controlsElement) {
                controlsElement.classList.add('hide');
            }
            
            // Ocultar TODAS las dimensiones cuando se desactiva
            dimElements.forEach(dim => {
                dim.style.opacity = '0';
                dim.style.visibility = 'hidden';
            });
            
            // Ocultar todas las líneas también
            const allDimLines = modelViewer.querySelectorAll('.dimensionLine');
            allDimLines.forEach(line => {
                line.classList.add('hide');
            });
            
            // Detener el intervalo de actualización
            if (dimensionUpdateInterval) {
                clearInterval(dimensionUpdateInterval);
                dimensionUpdateInterval = null;
            }
        }

        // Renderizar el SVG con las líneas de dimensión
        if (dimensionsVisible) {
            renderSVG();
        }
    }
    
    if (toggleDimensionsButton) {
        toggleDimensionsButton.addEventListener('click', toggleDimensions);
    }

    const unitSystem = modelViewer.querySelector('#unit-system');

    // Almacenar las dimensiones originales para conversión
    let dimensions = {
        width: 0,  // x
        height: 0, // y
        depth: 0   // z
    };

    // Función para actualizar los textos de todas las dimensiones
    function updateAllDimensionTexts() {
        const isMetric = unitSystem.value === 'metric';
        if (!dimensions.width) return;

        const widthValue = isMetric ? dimensions.width : dimensions.width / 2.54;
        const heightValue = isMetric ? dimensions.height : dimensions.height / 2.54;
        const depthValue = isMetric ? dimensions.depth : dimensions.depth / 2.54;

        const widthText = isMetric ?
            `${widthValue.toFixed(0)} cm` :
            `${widthValue.toFixed(1)} in`;

        const heightText = isMetric ?
            `${heightValue.toFixed(0)} cm` :
            `${heightValue.toFixed(1)} in`;

        const depthText = isMetric ?
            `${depthValue.toFixed(0)} cm` :
            `${depthValue.toFixed(1)} in`;

        // Actualizar ambos lados
        modelViewer.querySelector('button[slot="hotspot-dim+Y-Z"]').textContent = widthText;
        modelViewer.querySelector('button[slot="hotspot-dim+X-Z"]').textContent = heightText;
        modelViewer.querySelector('button[slot="hotspot-dim+X-Y"]').textContent = depthText;
        
        // También actualizar las dimensiones traseras
        const backHeightElem = modelViewer.querySelector('button[slot="hotspot-dim-X-Z"]');
        const backDepthElem = modelViewer.querySelector('button[slot="hotspot-dim-X-Y"]');
        
        if (backHeightElem) backHeightElem.textContent = heightText;
        if (backDepthElem) backDepthElem.textContent = depthText;
    }

    // Reemplazar la función updateUnits
    function updateUnits() {
        updateAllDimensionTexts();
    }

    // Evento para cambiar de sistema de unidades
    if (unitSystem) {
        unitSystem.addEventListener('change', updateUnits);
    }

    // Función para dibujar líneas - optimizada para mejor rendimiento
    let animationFrame;
    function drawLine(svgLine, dotHotspot1, dotHotspot2) {
        if (!dotHotspot1 || !dotHotspot2) return; // No dibujar si algún punto no existe
        
        svgLine.setAttribute('x1', dotHotspot1.canvasPosition.x);
        svgLine.setAttribute('y1', dotHotspot1.canvasPosition.y);
        svgLine.setAttribute('x2', dotHotspot2.canvasPosition.x);
        svgLine.setAttribute('y2', dotHotspot2.canvasPosition.y);
        
        // Siempre mostrar todas las líneas sin importar el ángulo
        svgLine.classList.remove('hide');
    }

    const dimLines = modelViewer.querySelectorAll('line');

    // Mostrar u ocultar dimensiones según el ángulo de la cámara
    function updateDimensionVisibility() {
        // Solo actualizar si las dimensiones están activas
        if (!dimensionsVisible) {
            return;
        }
        
        const cameraOrbit = modelViewer.getCameraOrbit();
        const theta = cameraOrbit.theta * (180 / Math.PI); // Convertir a grados
        
        // Determinar si estamos viendo el frente o la parte trasera
        // Frente: aproximadamente 0-90 o 270-360 grados
        // Atrás: aproximadamente 90-270 grados
        const isViewingFront = (theta < 90 || theta > 270);
        
        // Mostrar u ocultar botones según el ángulo de vista
        dimElements.forEach(dim => {
            const slot = dim.getAttribute('slot');
            // Si contiene -X y estamos viendo el frente, ocultarla
            // Si contiene +X y estamos viendo la parte trasera, ocultarla
            if ((slot.includes('-X') && isViewingFront) || 
                (slot.includes('+X') && !isViewingFront)) {
                dim.style.opacity = '0';
                dim.style.visibility = 'hidden';
            } else {
                dim.style.opacity = '1';
                dim.style.visibility = 'visible';
            }
        });
    }

    // Versión optimizada del renderizado SVG
    const renderSVG = () => {
        // Solo renderizar si las dimensiones están visibles
        if (!dimensionsVisible) return;
        
        // Cancelar cualquier frame de animación pendiente
        if (animationFrame) {
            cancelAnimationFrame(animationFrame);
        }
        
        // Actualizar visibilidad de dimensiones según el ángulo de vista
        updateDimensionVisibility();
        
        // Dibujar inmediatamente todas las líneas
        // Esto elimina el retraso causado por requestAnimationFrame
        drawLine(
            dimLines[0],
            modelViewer.queryHotspot('hotspot-dot+X-Y+Z'),
            modelViewer.queryHotspot('hotspot-dot+X-Y-Z')
        );
        drawLine(
            dimLines[1],
            modelViewer.queryHotspot('hotspot-dot+X-Y-Z'),
            modelViewer.queryHotspot('hotspot-dot+X+Y-Z')
        );
        drawLine(
            dimLines[2],
            modelViewer.queryHotspot('hotspot-dot+X+Y-Z'),
            modelViewer.queryHotspot('hotspot-dot-X+Y-Z')
        );
        drawLine(
            dimLines[3],
            modelViewer.queryHotspot('hotspot-dot-X+Y-Z'),
            modelViewer.queryHotspot('hotspot-dot-X-Y-Z')
        );
        drawLine(
            dimLines[4],
            modelViewer.queryHotspot('hotspot-dot-X-Y-Z'),
            modelViewer.queryHotspot('hotspot-dot-X-Y+Z')
        );
    };

    modelViewer.addEventListener('load', () => {
        const center = modelViewer.getBoundingBoxCenter();
        const size = modelViewer.getDimensions();
        const x2 = size.x / 2;
        const y2 = size.y / 2;
        const z2 = size.z / 2;

        // Guardar dimensiones en centímetros para conversiones posteriores
        dimensions = {
            width: size.x,  // ancho (x)
            height: size.y, // alto (y)
            depth: size.z   // profundidad (z)
        };

        modelViewer.updateHotspot({
            name: 'hotspot-dot+X-Y+Z',
            position: `${center.x + x2} ${center.y - y2} ${center.z + z2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dim+X-Y',
            position: `${center.x + x2 * 1.05} ${center.y - y2 * 1.1} ${center.z}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dot+X-Y-Z',
            position: `${center.x + x2} ${center.y - y2} ${center.z - z2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dim+X-Z',
            position: `${center.x + x2 * 1.05} ${center.y} ${center.z - z2 * 1.2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dot+X+Y-Z',
            position: `${center.x + x2} ${center.y + y2} ${center.z - z2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dim+Y-Z',
            position: `${center.x} ${center.y + y2 * 1.1} ${center.z - z2 * 1.1}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dot-X+Y-Z',
            position: `${center.x - x2} ${center.y + y2} ${center.z - z2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dim-X-Z',
            position: `${center.x - x2 * 1.05} ${center.y} ${center.z - z2 * 1.2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dot-X-Y-Z',
            position: `${center.x - x2} ${center.y - y2} ${center.z - z2}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dim-X-Y',
            position: `${center.x - x2 * 1.05} ${center.y - y2 * 1.1} ${center.z}`
        });

        modelViewer.updateHotspot({
            name: 'hotspot-dot-X-Y+Z',
            position: `${center.x - x2} ${center.y - y2} ${center.z + z2}`
        });

        // Guardar el estado inicial de interacción del modelo
        const initialAttributes = {
            cameraControls: modelViewer.hasAttribute('camera-controls'),
            disableZoom: modelViewer.hasAttribute('disable-zoom'),
            disablePan: modelViewer.hasAttribute('disable-pan'),
            disableTap: modelViewer.hasAttribute('disable-tap')
        };

        // Actualizar unidades iniciales
        updateUnits();

        // Ya no necesitamos eliminar etiquetas porque queremos mostrar/ocultar según el ángulo
        const backLabels = [
            'hotspot-dim-X-Z',
            'hotspot-dim-X-Y'
        ];
        
        // Actualizar texto en dimensiones traseras
        backLabels.forEach(labelId => {
            const elem = modelViewer.querySelector(`button[slot="${labelId}"]`);
            if (elem) {
                // Asignar el texto adecuado
                if (labelId === 'hotspot-dim-X-Z') {
                    elem.textContent = heightText;
                } else if (labelId === 'hotspot-dim-X-Y') {
                    elem.textContent = depthText;
                }
                elem.style.display = 'block'; // Asegurar que sea visible
            }
        });

        // Asegurarse de que todas las dimensiones estén ocultas inicialmente
        dimElements.forEach(dim => {
            dim.style.opacity = '0';
            dim.style.visibility = 'hidden';
        });
        
        const allDimLines = modelViewer.querySelectorAll('.dimensionLine');
        allDimLines.forEach(line => {
            line.classList.add('hide');
        });

        // Renderizar SVG inicial
        renderSVG();

        // Usar un evento más eficiente para actualizar las líneas
        modelViewer.addEventListener('camera-change', () => {
            if (dimensionsVisible) {
                renderSVG(); // Renderizar inmediatamente sin throttling
            }
        });
    });
    
    // Ejecutar optimizaciones
    optimizeModel();
});

// Función para detectar elementos en el viewport y aplicar animaciones al hacer scroll
function initScrollReveal() {
    // Seleccionar todos los elementos que queremos animar
    const elementsToAnimate = document.querySelectorAll('p, h1, h2, h3, .footer-section');

    // Verificar si estamos en un dispositivo móvil
    const isMobile = window.innerWidth <= 768;

    // Función para verificar si un elemento está en el viewport
    function isElementInViewport(el) {
        const rect = el.getBoundingClientRect();
        return (
            rect.top <= (window.innerHeight || document.documentElement.clientHeight) * 0.85 &&
            rect.bottom >= 0
        );
    }

    // Función para activar las animaciones de los elementos visibles
    function checkVisibility() {
        elementsToAnimate.forEach(element => {
            if (isElementInViewport(element)) {
                if (element.classList.contains('scroll-reveal')) {
                    element.classList.add('active');
                }
                if (element.classList.contains('text-animation')) {
                    element.classList.add('animate');
                }
            }
        });
    }

    // Verificar visibilidad al cargar la página
    checkVisibility();

    // Verificar visibilidad al hacer scroll
    window.addEventListener('scroll', checkVisibility);
}

// Función para manejar el header al hacer scroll
function initHeaderScrollEffect() {
    const header = document.querySelector('.header');
    let lastScrollTop = 0;
    let headerHeight = header.offsetHeight;
    
    window.addEventListener('scroll', function() {
        let currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        
        // Si estamos en la parte superior de la página, siempre mostrar el header
        if (currentScroll <= 50) {
            header.style.transform = 'translateY(0)';
            header.style.transition = 'transform 0.3s ease';
            return;
        }
        
        // Si scrolleamos hacia abajo más allá de la altura del header, ocultarlo
        if (currentScroll > lastScrollTop && currentScroll > headerHeight) {
            header.style.transform = 'translateY(-100%)';
            header.style.transition = 'transform 0.3s ease';
        } 
        // Si scrolleamos hacia arriba, mostrar el header
        else if (currentScroll < lastScrollTop) {
            header.style.transform = 'translateY(0)';
            header.style.transition = 'transform 0.3s ease';
        }
        
        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll; // Para navegadores móviles
    }, { passive: true });
}

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar las animaciones al hacer scroll
    initScrollReveal();
    
    // Inicializar el efecto del header al hacer scroll
    initHeaderScrollEffect();

    // Manejar el envío del formulario
    const contactForm = document.getElementById('contactForm');
    const formMessage = document.getElementById('formMessage');

    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            // FormSubmit manejará el envío real
            // Aquí solo mostramos un mensaje de confirmación
            setTimeout(function() {
                formMessage.className = 'form-message success';
                formMessage.textContent = '¡Mensaje enviado con éxito! Te responderemos pronto.';
                formMessage.style.display = 'block';
                contactForm.reset();
            }, 1000);
        });
    }
});