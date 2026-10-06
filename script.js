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

// Prepare entrances outside the viewport so visible content never jumps backwards.
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
if (!motionPreference.matches && 'IntersectionObserver' in window && 'animate' in Element.prototype) {
  const selectors = [
    '.intro-main > *', '.section-heading-row', '.service-card',
    '.emergency-copy', '.image-statement-copy p', '.work-areas-grid article',
    '.coverage-copy', '.coverage-hours', '.process-grid article', '.start-grid article',
    '.project-feature-body', '.document-promo > div', '.contact-intro', '.contact-form'
  ];
  const pending = new Set();
  const active = new Map();
  const delays = new Map();
  const ease = 'cubic-bezier(.22, 1, .36, 1)';
  const viewportHeight = document.documentElement.clientHeight;
  // Batch geometry reads before adding any motion styles.
  const items = [...document.querySelectorAll(selectors.join(', '))].map(item => ({
    item, top: item.getBoundingClientRect().top
  }));
  const rows = new Map();

  function settle(item) {
    observer.unobserve(item);
    pending.delete(item);
    item.classList.remove('motion-pending');
    active.get(item)?.cancel();
    active.delete(item);
    item.classList.remove('motion-running');
  }

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting || !pending.has(entry.target)) return;
      const item = entry.target;
      observer.unobserve(item);
      pending.delete(item);
      // Preferences and background tabs settle immediately; crossed content finishes quickly.
      if (document.hidden || motionPreference.matches) {
        settle(item);
        return;
      }
      const crossed = entry.boundingClientRect.top < 0;
      const fadeOnly = item.matches('.coverage-hours, .contact-form');
      const frames = fadeOnly
        ? [{ opacity: .58 }, { opacity: 1 }]
        : [{ opacity: .58, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }];
      try {
        const animation = item.animate(frames, {
          duration: crossed ? 180 : (fadeOnly ? 650 : 620),
          delay: crossed ? 0 : (delays.get(item) || 0),
          easing: ease,
          // Hold the prepared frame during stagger delays, never flash the final frame.
          fill: 'backwards'
        });
        item.classList.remove('motion-pending');
        item.classList.add('motion-running');
        active.set(item, animation);
        const cleanup = () => {
          active.delete(item);
          item.classList.remove('motion-running');
        };
        animation.onfinish = cleanup;
        animation.oncancel = cleanup;
      } catch {
        settle(item);
      }
    });
  }, { threshold: 0, rootMargin: '0px 0px 80px 0px' });

  items.forEach(({ item, top }) => {
    // Keep initially visible and near-visible content untouched.
    if (top < viewportHeight + 80) return;
    if (item.matches('.service-card, .work-areas-grid article, .process-grid article, .start-grid article')) {
      const previous = rows.get(item.parentElement);
      const column = previous && Math.abs(previous.top - top) < 8 ? previous.column + 1 : 0;
      rows.set(item.parentElement, { top, column });
      delays.set(item, Math.min(column * 60, 120));
    }
    item.classList.add('motion-pending');
    pending.add(item);
    observer.observe(item);
  });

  motionPreference.addEventListener('change', event => {
    if (!event.matches) return;
    observer.disconnect();
    [...pending, ...active.keys()].forEach(settle);
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) [...active.keys()].forEach(settle);
  });
  document.addEventListener('focusin', event => {
    [...pending, ...active.keys()].forEach(item => {
      if (item.contains(event.target)) settle(item);
    });
  });
}
