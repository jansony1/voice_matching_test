// Polyfill for CredentialsContainer
if (typeof window !== 'undefined' && !window.CredentialsContainer) {
  window.CredentialsContainer = class CredentialsContainer {
    async get() { return null; }
    async store() { return null; }
    async create() { return null; }
  };
}
