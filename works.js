const photoLinks = [...document.querySelectorAll('.work-photo')];
const viewer = document.querySelector('.photo-viewer');

// The image links remain usable when JavaScript or native dialogs are unavailable.
if (viewer && typeof viewer.showModal === 'function') {
  const viewerImage = viewer.querySelector('.viewer-image');
  const viewerTitle = viewer.querySelector('#viewer-title');
  const viewerAddress = viewer.querySelector('#viewer-address');
  const viewerCount = viewer.querySelector('.viewer-count');
  const viewerError = viewer.querySelector('.viewer-error');
  let currentPhoto = 0;

  function showPhoto(index) {
    currentPhoto = (index + photoLinks.length) % photoLinks.length;
    const link = photoLinks[currentPhoto];
    const item = link.closest('.work-item');
    const photo = link.querySelector('img');
    const address = item.querySelector('.work-address').textContent.trim();
    viewerTitle.textContent = item.querySelector('h2').textContent;
    viewerAddress.textContent = address;
    viewerAddress.hidden = !address;
    viewerCount.textContent = `${currentPhoto + 1} / ${photoLinks.length}`;
    viewerError.hidden = true;
    viewerImage.hidden = false;
    viewerImage.alt = photo.alt;
    viewerImage.width = Number(photo.getAttribute('width'));
    viewerImage.height = Number(photo.getAttribute('height'));
    viewerImage.src = link.href;
  }

  photoLinks.forEach((link, index) => link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    showPhoto(index);
    viewer.showModal();
    document.documentElement.classList.add('photo-viewer-open');
  }));

  viewer.querySelector('.viewer-close').addEventListener('click', () => viewer.close());
  viewer.querySelector('.viewer-previous').addEventListener('click', () => showPhoto(currentPhoto - 1));
  viewer.querySelector('.viewer-next').addEventListener('click', () => showPhoto(currentPhoto + 1));
  viewer.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      showPhoto(currentPhoto + (event.key === 'ArrowRight' ? 1 : -1));
    }
  });
  viewer.addEventListener('click', event => {
    if (event.target !== viewer) return;
    const bounds = viewer.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) viewer.close();
  });
  viewer.addEventListener('close', () => document.documentElement.classList.remove('photo-viewer-open'));
  viewerImage.addEventListener('error', () => {
    viewerImage.hidden = true;
    viewerError.hidden = false;
  });
}
