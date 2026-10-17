document.addEventListener('DOMContentLoaded', () => {
  const field = document.querySelector('#id_body');
  if (!field) return;
  const wrapper = field.closest('.cms-editor-wrap');
  const rich = wrapper.querySelector('.cms-rich-editor');
  const notice = wrapper.querySelector('.cms-editor-error');
  const form = field.closest('form');
  if (!window.Quill || !window.TurndownService) {
    notice.textContent = 'Редактор не загрузился. Обновите страницу и попробуйте снова.';
    notice.hidden = false;
    form.addEventListener('submit', event => event.preventDefault());
    return;
  }
  const editor = new Quill(rich, {
    modules: { toolbar: false },
    formats: ['header', 'bold', 'italic', 'list', 'link'],
    placeholder: 'Напишите текст статьи…',
  });
  editor.root.setAttribute('role', 'textbox');
  editor.root.setAttribute('aria-label', 'Текст статьи');
  editor.root.setAttribute('aria-multiline', 'true');
  editor.root.setAttribute('spellcheck', 'true');
  editor.root.id = 'article-text';
  editor.root.setAttribute('aria-describedby', 'id_body_helptext');
  document.querySelector('label[for="id_body"]')?.setAttribute('for', 'article-text');
  const converter = new TurndownService({ headingStyle: 'atx', bulletListMarker: '-', emDelimiter: '*' });
  const buttons = [...wrapper.querySelectorAll('[data-format]')];
  let dirty = false;
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
  form.addEventListener('input', () => { dirty = true; });
  form.addEventListener('submit', event => {
    if (!editor.getText().trim()) {
      event.preventDefault();
      notice.textContent = 'Добавьте текст статьи.';
      notice.hidden = false;
      editor.focus();
      return;
    }
    field.value = converter.turndown(editor.getSemanticHTML());
    if (field.value.length > 100000) {
      event.preventDefault();
      notice.textContent = 'Текст слишком длинный. Разделите его на несколько статей.';
      notice.hidden = false;
      return;
    }
    dirty = false;
  });
  window.addEventListener('beforeunload', event => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
});
