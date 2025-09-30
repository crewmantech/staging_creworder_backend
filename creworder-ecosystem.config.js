module.exports = {
    apps: [
      {
        name: "creworder-gunicorn",
        script: "/home/creworder.com/public_html/Creworder_backend/start_backend.sh",
        interpreter: "bash",
        uid: 0,
      gid: 0,
      },
      {
        name: "creworder-celery-worker",
        script: "celery",
        args: "-A creworder_backend worker --loglevel=info",
        cwd: "/home/creworder.com/public_html/Creworder_backend",
        interpreter: "bash",
        env: {
          DJANGO_SETTINGS_MODULE: "creworder_backend.settings",
        },
        uid: 0,
      gid: 0,
      },
      {
        name: "creworder-celery-beat",
        script: "celery",
        args: "-A creworder_backend beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler",
        cwd: "/home/creworder.com/public_html/Creworder_backend",
        interpreter: "bash",
        env: {
          DJANGO_SETTINGS_MODULE: "creworder_backend.settings",
        },
        uid: 0,
      gid: 0,
      }
    ]
  }
  