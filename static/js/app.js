// JavaScript for Krishi Sakhi

// Voice recognition functionality
function startVoiceRecognition() {
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.start();

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('message-input').value = transcript;
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
        };
    } else {
        alert('Speech recognition is not supported in your browser.');
    }
}

// Text-to-speech functionality
async function speakText(text) {
    try {
        const response = await fetch('/text_to_speech', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({text: text})
        });
        
        const data = await response.json();
        if (data.audio) {
            const audio = new Audio('data:audio/mp3;base64,' + data.audio);
            audio.play();
        }
    } catch (error) {
        console.error('Text-to-speech error:', error);
    }
}

// Auto-refresh weather data
function refreshWeather() {
    fetch('/weather')
        .then(response => response.json())
        .then(data => {
            // Update weather display
            console.log('Weather updated:', data);
        })
        .catch(error => console.error('Weather refresh error:', error));
}