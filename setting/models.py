from django.db import models
from core.models import Supplier,City
from Medical_device.models import Category

class Industry(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class SupplierProfile(models.Model):
    user = models.OneToOneField(Supplier, on_delete=models.CASCADE)
    industries = models.ManyToManyField(Industry, blank=True)
    specialized_equipment = models.ManyToManyField(Category, blank=True)
    cities = models.ManyToManyField(City, blank=True)


    def __str__(self):
        return f"{self.user.name} Profile"

