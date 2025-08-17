// QR Generator functionality
document.addEventListener('DOMContentLoaded', function() {
    const qrForm = document.getElementById('qrForm');
    if (qrForm) {
        qrForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(qrForm);
            const data = Object.fromEntries(formData.entries());
            
            fetch('/generate_qr', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const qrImageContainer = document.getElementById('qrImageContainer');
                    qrImageContainer.innerHTML = `
                        <img src="${data.qr_url}" alt="Generated QR Code" style="max-width: 300px;">
                        <p>QR Code generated successfully!</p>
                    `;
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }
    
    // QR Scanner functionality
    const video = document.getElementById('scanner');
    if (video) {
        const scanResult = document.getElementById('scanResult');
        
        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
            .then(function(stream) {
                video.srcObject = stream;
                video.setAttribute("playsinline", true); // required for iOS
                video.play();
                requestAnimationFrame(tick);
            })
            .catch(function(err) {
                console.error("Error accessing camera: ", err);
                scanResult.textContent = "Could not access camera: " + err.message;
            });
        
        function tick() {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                });
                
                if (code) {
                    scanResult.innerHTML = `
                        <p>Scanned Data:</p>
                        <pre>${code.data}</pre>
                        <p>Scan another code in 3 seconds...</p>
                    `;
                    setTimeout(() => {
                        scanResult.innerHTML = '<p>Ready to scan...</p>';
                    }, 3000);
                }
            }
            requestAnimationFrame(tick);
        }
    }
});

// Mobile menu toggle
const mobileMenu = document.getElementById('mobile-menu');
const navbarMenu = document.querySelector('.navbar-menu');

mobileMenu.addEventListener('click', () => {
    mobileMenu.classList.toggle('active');
    navbarMenu.classList.toggle('active');
});

// Close menu when clicking on a link
document.querySelectorAll('.navbar-link').forEach(link => {
    link.addEventListener('click', () => {
        mobileMenu.classList.remove('active');
        navbarMenu.classList.remove('active');
    });
});