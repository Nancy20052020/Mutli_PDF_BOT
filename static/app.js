const pdfInput = document.getElementById('pdfInput');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const answerSection = document.getElementById('answerSection');
const answerText = document.getElementById('answerText');
const audioPlayer = document.getElementById('audioPlayer');

sendBtn.addEventListener('click', async () => {
  if (!pdfInput.files.length) {
    alert('Please upload at least one PDF.');
    return;
  }
  if (!queryInput.value.trim()) {
    alert('Please enter a question.');
    return;
  }

  const formData = new FormData();
  for (const file of pdfInput.files) {
    formData.append('pdfs', file);
  }
  formData.append('query', queryInput.value.trim());

  sendBtn.disabled = true;
  sendBtn.textContent = 'Processing...';
  answerSection.hidden = true;

  try {
    const response = await fetch('http://localhost:5000/api/query', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || 'Server error');
    }

    const data = await response.json();
    answerText.textContent = data.answer || 'No answer found.';
    if (data.audio_base64) {
      audioPlayer.src = "data:audio/mpeg;base64," + data.audio_base64;
      audioPlayer.play();
    } else {
      audioPlayer.src = "";
    }
    answerSection.hidden = false;
  } catch (err) {
    alert('Error: ' + err.message);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
  }
});
