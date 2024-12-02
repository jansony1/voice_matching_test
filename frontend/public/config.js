// Runtime configuration
window.configs = {
  // Default to localhost for development, will be replaced by docker-entrypoint.sh
  BACKEND_URL: 'http://localhost:8000/api'
};

console.log('Config loaded:', window.configs);
