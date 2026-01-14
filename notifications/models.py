from django.db import models

class TelegramSubscriber(models.Model):
    chat_id = models.BigIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.chat_id)
