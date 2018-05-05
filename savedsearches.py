From

class SavedTrips(Model):
    fuel_type = TextField()
    fuel_economy = TextField()

    class Meta:
        database = DATABASE