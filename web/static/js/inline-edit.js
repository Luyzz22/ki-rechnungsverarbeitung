// Inline Editing für Rechnungen
document.addEventListener('DOMContentLoaded', function() {
  const editableCells = document.querySelectorAll('.editable');
  
  editableCells.forEach(cell => {
    // Speichere Originalwert
    cell.dataset.original = cell.textContent.trim();
    
    // Click to edit
    cell.addEventListener('click', function() {
      if (this.classList.contains('editing')) return;
      
      const currentValue = this.textContent.trim();
      const field = this.dataset.field;
      
      this.classList.add('editing');
      this.innerHTML = `<input type="text" value="${currentValue}" class="edit-input">`;
      const input = this.querySelector('input');
      input.focus();
      input.select();
      
      // Save on blur or enter
      const saveEdit = async () => {
        const newValue = input.value.trim();
        const invoiceId = this.closest('tr').dataset.invoiceId;
        
        if (newValue !== this.dataset.original) {
          // Save to server
          try {
            const response = await fetch(`/api/invoice/${invoiceId}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ [field]: newValue })
            });
            
            if (response.ok) {
              this.dataset.original = newValue;
              this.classList.add('edited');
              showToast('✓ Gespeichert & gelernt');
            } else {
              showToast('❌ Fehler beim Speichern', 'error');
            }
          } catch (e) {
            showToast('❌ Fehler beim Speichern', 'error');
          }
        }
        
        this.classList.remove('editing');
        this.textContent = input.value.trim();
      };
      
      input.addEventListener('blur', saveEdit);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') saveEdit();
        if (e.key === 'Escape') {
          this.classList.remove('editing');
          this.textContent = this.dataset.original;
        }
      });
    });
  });
});

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}
