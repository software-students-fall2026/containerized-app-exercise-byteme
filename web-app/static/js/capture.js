
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const photo = document.getElementById('photo');
const start_btn = document.getElementById('start_btn');
const photo_btn = document.getElementById('photo_btn');
const file_input = document.getElementById('file_input');
const status_msg = document.getElementById('status');
let stream = null;

start_btn.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
        video: {width: 1280, height: 720, facingMode: 'environment'},
        audio: false
    });
    video.srcObject = stream;
    video.style.display = 'block';
    photo_btn.disabled = false;
    status_msg.textContent = '';
    }
    catch(error){
        status_msg.textContent = 'Camera unavailable. Use localhost/HTTPS, or upload a picture';
    }
});

async function uploadImage(blob, filename){
    const form = new FormData();
    form.append('image', blob, filename);
    status_msg.textContent = "Uploading...";

    try{
        const r = await fetch ('/upload', { method: 'POST', body: form});
        const result = await r.json();

        if(r.ok){
          status_msg.textContent = 'Found: ' + JSON.stringify(result.counts);
        }
        else{
          status_msg.textContent = 'Error: ' + (result.error || r.status);
        }
    }
    catch(error){
        status_msg.textContent = 'Upload Failed: ' + error.message;
    }
}

photo_btn.addEventListener('click', () => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

    if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
    }
    video.srcObject = null;
    photo_btn.disabled = true;
    video.style.display = 'none';

    canvas.toBlob(
        (blob) => {
          photo.src = URL.createObjectURL(blob);
          uploadImage(blob, 'capture.jpg');
        },
        'image/jpeg', 0.9
    );
      
});

file_input.addEventListener('change', () =>{
    if(stream){
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
    }
    video.srcObject = null;
    photo_btn.disabled = true;
    video.style.display = 'none';

    const file = file_input.files[0];
    if (file){
        photo.src = URL.createObjectURL(file);
        uploadImage(file, file.name);
    }
});
