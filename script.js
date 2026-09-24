const menuButton = document.querySelector('.menu-toggle');
const mobileMenu = document.querySelector('.mobile-menu');

menuButton.addEventListener('click', () => {
  const open = menuButton.getAttribute('aria-expanded') !== 'true';
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
  mobileMenu.hidden = !open;
});

mobileMenu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  mobileMenu.hidden = true;
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.setAttribute('aria-label', 'Открыть меню');
}));

const fileInput = document.querySelector('#files');
const fileList = document.querySelector('#file-list');
const dropzone = document.querySelector('#dropzone');
const selectedFiles = new DataTransfer();

function renderFiles() {
  fileList.replaceChildren();
  [...selectedFiles.files].forEach((file, index) => {
    const item = document.createElement('li');
    const label = document.createElement('span');
    const remove = document.createElement('button');
    label.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} МБ`;
    remove.type = 'button';
    remove.textContent = 'Убрать';
    remove.setAttribute('aria-label', `Убрать файл ${file.name}`);
    remove.addEventListener('click', () => {
      const remaining = [...selectedFiles.files].filter((_, i) => i !== index);
      selectedFiles.items.clear();
      remaining.forEach(entry => selectedFiles.items.add(entry));
      fileInput.files = selectedFiles.files;
      renderFiles();
    });
    item.append(label, remove);
    fileList.append(item);
  });
}

function addFiles(files) {
  const allowed = /\.(pdf|doc|docx|xls|xlsx|dwg|dxf|zip)$/i;
  const chosen = [...files];
  const invalid = chosen.filter(file => !allowed.test(file.name));
  const message = document.querySelector('#form-status');
  if (invalid.length) {
    message.classList.remove('is-info');
    message.textContent = 'Поддерживаются PDF, DOC, DOCX, XLS, XLSX, DWG, DXF и ZIP. Выберите файл в одном из этих форматов.';
  } else {
    message.textContent = '';
  }
  chosen.filter(file => allowed.test(file.name)).forEach(file => {
    const duplicate = [...selectedFiles.files].some(entry => entry.name === file.name && entry.size === file.size);
    if (!duplicate) selectedFiles.items.add(file);
  });
  fileInput.files = selectedFiles.files;
  renderFiles();
}

fileInput.addEventListener('change', event => addFiles(event.target.files));
['dragenter', 'dragover'].forEach(name => dropzone.addEventListener(name, event => {
  event.preventDefault();
  dropzone.classList.add('is-dragover');
}));
['dragleave', 'drop'].forEach(name => dropzone.addEventListener(name, event => {
  event.preventDefault();
  dropzone.classList.remove('is-dragover');
}));
dropzone.addEventListener('drop', event => addFiles(event.dataTransfer.files));

const form = document.querySelector('#inquiry-form');
const status = document.querySelector('#form-status');
form.addEventListener('submit', event => {
  event.preventDefault();
  status.classList.remove('is-info');
  const name = form.elements.name;
  const phone = form.elements.phone;
  [name, phone].forEach(field => field.removeAttribute('aria-invalid'));
  if (!name.value.trim() || !phone.value.trim()) {
    if (!name.value.trim()) name.setAttribute('aria-invalid', 'true');
    if (!phone.value.trim()) phone.setAttribute('aria-invalid', 'true');
    status.textContent = 'Заполните имя и телефон, чтобы продолжить.';
    (!name.value.trim() ? name : phone).focus();
    return;
  }
  status.classList.add('is-info');
  status.textContent = 'Заявка не отправлена: приём обращений через сайт ещё не подключён.';
});

// Motion follows the page's reading order; content stays visible if scripts stop.
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!reduceMotion && 'IntersectionObserver' in window && 'animate' in Element.prototype) {
  const animatedItems = document.querySelectorAll('.service-card, .emergency-copy, .work-areas-grid article, .coverage-hours, .process-grid article, .project-feature, .document-promo h2');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const item = entry.target;
      item.animate([
        { opacity: .72, transform: 'translateY(18px)' },
        { opacity: 1, transform: 'translateY(0)' }
      ], {
        duration: 720,
        delay: Number(item.dataset.motionIndex || 0) * 90,
        easing: 'cubic-bezier(.16, 1, .3, 1)'
      });
      observer.unobserve(item);
    });
  }, { threshold: .12, rootMargin: '0px 0px -7% 0px' });
  animatedItems.forEach((item, index) => {
    item.dataset.motionIndex = index % 3;
    observer.observe(item);
  });
}
