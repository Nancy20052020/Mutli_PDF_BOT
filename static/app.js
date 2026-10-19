const pdfInput = document.getElementById("pdfInput");
const dropzone = document.getElementById("dropzone");
const fileList = document.getElementById("fileList");
const fileCount = document.getElementById("fileCount");
const queryInput = document.getElementById("queryInput");
const sendBtn = document.getElementById("sendBtn");
const status = document.getElementById("status");
const banner = document.getElementById("banner");
const answerSection = document.getElementById("answerSection");
const answerText = document.getElementById("answerText");
const ttsNote = document.getElementById("ttsNote");
const audioPlayer = document.getElementById("audioPlayer");

const MAX_FILES = 5;
const MAX_BYTES = 4 * 1024 * 1024;
let selectedFiles = [];

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("is-error", isError);
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderFiles() {
  fileList.replaceChildren();
  selectedFiles.forEach((file, index) => {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = file.name;
    const size = document.createElement("span");
    size.className = "file-size";
    size.textContent = formatSize(file.size);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "ghost";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      selectedFiles.splice(index, 1);
      renderFiles();
    });
    item.append(name, size, remove);
    fileList.append(item);
  });
  fileCount.textContent = selectedFiles.length ? `${selectedFiles.length} selected` : "None yet";
}

function addFiles(fileListLike) {
  const next = [...selectedFiles];
  for (const file of fileListLike) {
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setStatus(`${file.name} is not a PDF.`, true);
      continue;
    }
    if (file.size > MAX_BYTES) {
      setStatus(`${file.name} is larger than 4 MB.`, true);
      continue;
    }
    if (next.length >= MAX_FILES) {
      setStatus(`You can add up to ${MAX_FILES} PDFs.`, true);
      break;
    }
    if (!next.some((item) => item.name === file.name && item.size === file.size)) {
      next.push(file);
    }
  }
  selectedFiles = next;
  renderFiles();
}

pdfInput.addEventListener("change", () => {
  addFiles(pdfInput.files);
  pdfInput.value = "";
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-over");
  });
});

dropzone.addEventListener("drop", (event) => {
  addFiles(event.dataTransfer.files);
});

queryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendQuestion();
  }
});

sendBtn.addEventListener("click", sendQuestion);

async function sendQuestion() {
  if (!selectedFiles.length) {
    setStatus("Add at least one PDF.", true);
    return;
  }
  const query = queryInput.value.trim();
  if (!query) {
    setStatus("Enter a question.", true);
    queryInput.focus();
    return;
  }

  const formData = new FormData();
  selectedFiles.forEach((file) => formData.append("pdfs", file));
  formData.append("query", query);

  sendBtn.disabled = true;
  sendBtn.textContent = "Reading…";
  setStatus("Reading the PDFs and writing an answer.");
  answerSection.hidden = true;

  try {
    const response = await fetch("/api/query", { method: "POST", body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "The server could not answer that.");
    }

    answerText.textContent = data.answer || "No answer found.";
    const notes = [];
    if (Array.isArray(data.notices)) notes.push(...data.notices.filter(Boolean));
    if (data.audio_note) notes.push(data.audio_note);
    if (notes.length) {
      ttsNote.hidden = false;
      ttsNote.textContent = notes.join(" ");
    } else {
      ttsNote.hidden = true;
      ttsNote.textContent = "";
    }
    if (data.audio_base64) {
      audioPlayer.hidden = false;
      audioPlayer.src = `data:audio/mpeg;base64,${data.audio_base64}`;
      audioPlayer.play().catch(() => {});
    } else {
      audioPlayer.hidden = true;
      audioPlayer.removeAttribute("src");
    }
    answerSection.hidden = false;
    setStatus("");
    answerSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Ask";
  }
}

fetch("/api/health")
  .then((response) => response.json())
  .then((data) => {
    if (!data.openai || !data.elevenlabs) {
      banner.hidden = false;
      banner.textContent = "This page is ready. Add OPENAI_API_KEY and ELEVEN_API_KEY before asking a question.";
    }
  })
  .catch(() => {});
