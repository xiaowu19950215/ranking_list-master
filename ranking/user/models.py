from django.db import models

# Create your models here.
class UserProfile(models.Model):

    username = models.CharField(max_length=11,verbose_name='用户昵称')
    password = models.CharField(max_length=50,verbose_name='密码')

    class Meta:
        db_table = 'user_profile'

    def __str__(self):
        return '%s,%s,%s' % (str(self.id),self.username,self.password)
