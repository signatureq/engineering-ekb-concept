document.addEventListener('DOMContentLoaded', () => {
  let dirty = false;
  const wire = wrapper => {
    if (wrapper.dataset.ready) return;
    const field = wrapper.querySelector('textarea');
    if (field.id.includes('__prefix__')) return;
    wrapper.dataset.ready = 'true';
    const rich = wrapper.querySelector('.cms-rich-editor');
    const notice = wrapper.querySelector('.cms-editor-error');
    const form = field.closest('form');
    if (!window.Quill || !window.TurndownService) {
      notice.textContent = 'Редактор не загрузился. Обновите страницу и попробуйте снова.';
      notice.hidden = false;
      form.addEventListener('submit', event => event.preventDefault());
      return;
    }
    const label = document.querySelector(`label[for="${field.id}"]`);
    const name = label?.textContent.replace(/:$/, '').trim() || 'Текст';
    const required = field.dataset.required === 'true';
    const editor = new Quill(rich, {
      modules: { toolbar: false },
      formats: ['header', 'bold', 'italic', 'list', 'link'],
      placeholder: 'Введите текст…',
    });
    editor.root.setAttribute('role', 'textbox');
    editor.root.setAttribute('aria-label', name);
    editor.root.setAttribute('aria-multiline', 'true');
    editor.root.setAttribute('spellcheck', 'true');
    editor.root.id = field.id + '-visual';
    label?.setAttribute('for', editor.root.id);
    const converter = new TurndownService({ headingStyle: 'atx', bulletListMarker: '-', emDelimiter: '*' });
    const buttons = [...wrapper.querySelectorAll('[data-format]')];
    const updateButtons = () => {
      const formats = editor.getFormat();
      buttons.forEach(button => button.setAttribute('aria-pressed', String(Boolean(formats[button.dataset.format]))));
    };
    buttons.forEach(button => {
      button.addEventListener('mousedown', event => event.preventDefault());
      button.addEventListener('click', () => {
        editor.focus();
        const format = button.dataset.format;
        const value = button.dataset.value === '2' ? 2 : button.dataset.value || true;
        editor.format(format, editor.getFormat()[format] ? false : value, 'user');
        updateButtons();
      });
    });
    editor.on('selection-change', updateButtons);
    editor.on('text-change', (_delta, _old, source) => {
      if (source === 'user') dirty = true;
      notice.hidden = true;
      updateButtons();
    });
    form.addEventListener('submit', event => {
      if (required && !editor.getText().trim()) {
        event.preventDefault();
        notice.textContent = 'Добавьте текст.';
        notice.hidden = false;
        editor.focus();
        return;
      }
      field.value = converter.turndown(editor.getSemanticHTML()).replace(/\u00a0/g, ' ');
      if (field.value.length > Number(field.getAttribute('maxlength') || 100000)) {
        event.preventDefault();
        notice.textContent = 'Текст слишком длинный. Сократите его и сохраните снова.';
        notice.hidden = false;
      }
    });
  };
  document.querySelectorAll('.cms-editor-wrap').forEach(wire);
  document.addEventListener('formset:added', event => event.target.querySelectorAll('.cms-editor-wrap').forEach(wire));
  document.querySelectorAll('#content-main form').forEach(form => {
    form.addEventListener('input', () => { dirty = true; });
    form.addEventListener('submit', event => { if (!event.defaultPrevented) dirty = false; });
  });
  window.addEventListener('beforeunload', event => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
});
