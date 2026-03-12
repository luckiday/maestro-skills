module.exports = {
  apps: [
    {
      name: 'teaching-docs-server',
      script: 'server.js',
      cwd: __dirname,
      env_file: '.env',
      env: {
        NODE_ENV: 'production',
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
    },
  ],
};
