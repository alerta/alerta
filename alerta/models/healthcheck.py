import os

from alerta.app import db


class HealthCheck:
    @staticmethod
    def health_check():
        response = db.health_check()
        return {"msg": response.msg, "time": response.time, "COMMIT_ID": os.environ.get('COMMIT_ID')}
