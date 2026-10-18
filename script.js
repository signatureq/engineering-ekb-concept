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

document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
    menuButton.click();
    menuButton.focus();
  }
});

// The same-origin server endpoint keeps mail credentials out of the public site.
if (document.querySelector('#inquiry-form')) {
  const fileInput = document.querySelector('#files');
  const fileList = document.querySelector('#file-list');
  const dropzone = document.querySelector('#dropzone');
  const selectedFiles = new DataTransfer();
  let requestId = null;

  function renderFiles() {
    requestId = null;
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
    const allowed = /\.(jpg|jpeg|png|webp|pdf|doc|docx|xls|xlsx|dwg|dxf|zip)$/i;
    const chosen = [...files];
    const invalid = chosen.filter(file => !allowed.test(file.name));
    const message = document.querySelector('#form-status');
    if (invalid.length) {
      message.classList.remove('is-info');
      message.textContent = 'Поддерживаются JPG, PNG, WebP, PDF, DOC, DOCX, XLS, XLSX, DWG, DXF и ZIP. Выберите файл в одном из этих форматов.';
    } else {
      message.textContent = '';
    }
    chosen.filter(file => allowed.test(file.name)).forEach(file => {
      const duplicate = [...selectedFiles.files].some(entry => entry.name === file.name && entry.size === file.size);
      const total = [...selectedFiles.files].reduce((sum, entry) => sum + entry.size, 0);
      if (!duplicate && (selectedFiles.files.length >= 5 || total + file.size > 10 * 1024 * 1024)) {
        message.classList.remove('is-info');
        message.textContent = 'Можно приложить до 5 файлов общим размером до 10 МБ.';
      } else if (!duplicate) selectedFiles.items.add(file);
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
  const requestedService = new URLSearchParams(window.location.search).get('service');
  if ([...form.elements.service.options].some(option => option.value === requestedService)) {
    form.elements.service.value = requestedService;
  }
  const status = document.querySelector('#form-status');
  const submit = form.querySelector('[type=submit]');
  const notice = form.querySelector('.form-demo-notice');
  const endpoint = '/api/inquiry/';
  const configPromise = fetch(endpoint, {credentials: 'same-origin', cache: 'no-store'})
    .then(response => response.ok ? response.json() : null)
    .then(config => {
      if (config?.enabled) notice.hidden = true;
      return config;
    }).catch(() => null);
  form.addEventListener('input', () => { requestId = null; });
  submit.disabled = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submit.disabled) return;
    status.classList.remove('is-info');
    const name = form.elements.name;
    const phone = form.elements.phone;
    [name, phone].forEach(field => field.removeAttribute('aria-invalid'));
    const validPhone = /^[+\d\s()\-]+$/.test(phone.value.trim()) && /^\d{10,15}$/.test(phone.value.replace(/\D/g, ''));
    if (!name.value.trim() || !validPhone) {
      if (!name.value.trim()) name.setAttribute('aria-invalid', 'true');
      if (!validPhone) phone.setAttribute('aria-invalid', 'true');
      status.textContent = 'Укажите имя и телефон с кодом города или оператора.';
      (!name.value.trim() ? name : phone).focus();
      return;
    }
    submit.disabled = true;
    const config = await configPromise;
    if (!config?.enabled) {
      status.classList.add('is-info');
      status.textContent = 'Отправка через форму пока недоступна. Пожалуйста, позвоните нам.';
      submit.disabled = false;
      return;
    }
    form.setAttribute('aria-busy', 'true');
    status.classList.add('is-info');
    status.textContent = 'Отправляем заявку…';
    const data = new FormData(form);
    requestId ||= crypto.randomUUID();
    data.set('request_id', requestId);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const result = await fetch(endpoint, {
        method: 'POST', body: data, credentials: 'same-origin', signal: controller.signal,
        headers: {'X-CSRFToken': config.csrfToken}
      });
      const answer = await result.json().catch(() => ({}));
      if (!result.ok || answer.ok !== true) {
        throw new Error(result.status === 429 ? 'Слишком много попыток. Подождите минуту или позвоните нам.' : answer.error || 'Не удалось отправить заявку. Попробуйте ещё раз или позвоните нам.');
      }
      form.reset();
      selectedFiles.items.clear();
      fileInput.files = selectedFiles.files;
      renderFiles();
      requestId = null;
      status.textContent = 'Заявка отправлена. Мы свяжемся с вами по указанному телефону.';
    } catch (error) {
      status.classList.remove('is-info');
      status.textContent = error.name === 'AbortError' || error instanceof TypeError
        ? 'Не удалось получить ответ. Данные остались в форме — попробуйте ещё раз или позвоните нам.'
        : error.message;
    } finally {
      clearTimeout(timeout);
      submit.disabled = false;
      form.removeAttribute('aria-busy');
    }
  });
}

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
