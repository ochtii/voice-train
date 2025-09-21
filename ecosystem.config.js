module.exports = {
  apps: [
    {
      name: 'voice-recog-backend',
      script: '/home/ochtii/voice-recog-pi/venv/bin/python',
      args: 'main.py',
      cwd: '/home/ochtii/voice-recog-pi/backend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/ochtii/voice-recog-pi/backend',
        PATH: '/home/ochtii/voice-recog-pi/venv/bin:/usr/local/bin:/usr/bin:/bin'
      },
      log_file: '/home/ochtii/voice-recog-pi/logs/combined.log',
      out_file: '/home/ochtii/voice-recog-pi/logs/out.log',
      error_file: '/home/ochtii/voice-recog-pi/logs/error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      kill_timeout: 5000,
      restart_delay: 3000
    },
    {
      name: 'auto-deployer',
      script: '/home/ochtii/voice-recog-pi/deployment/auto-deployer.py',
      interpreter: '/home/ochtii/voice-recog-pi/venv/bin/python',
      cwd: '/home/ochtii/voice-recog-pi/deployment',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/ochtii/voice-recog-pi',
        GITHUB_REPO: 'https://github.com/ochtii/voice-train.git',
        BRANCH: 'live',
        CHECK_INTERVAL: '5'
      },
      log_file: '/home/ochtii/voice-recog-pi/logs/deployer-combined.log',
      out_file: '/home/ochtii/voice-recog-pi/logs/deployer-out.log',
      error_file: '/home/ochtii/voice-recog-pi/logs/deployer-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      kill_timeout: 3000,
      restart_delay: 1000
    }
  ],
  
  deploy: {
    production: {
      user: 'ochtii',
      host: '192.168.188.92',
      ref: 'origin/live',
      repo: 'https://github.com/ochtii/voice-train.git',
      path: '/home/ochtii/voice-recog-pi',
      'pre-deploy-local': '',
      'post-deploy': 'source /home/ochtii/voice-recog-pi/venv/bin/activate && pip install -r backend/requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': 'mkdir -p /home/ochtii/voice-recog-pi/logs'
    }
  }
};