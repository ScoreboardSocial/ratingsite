import csv
import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from profiles.models import Profile

class Command(BaseCommand):
    help = 'Import profiles from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)

            required_columns = ['name', 'instagram', 'twitter', 'image_url']
            if not all(column in reader.fieldnames for column in required_columns):
                missing_columns = [column for column in required_columns if column not in reader.fieldnames]
                self.stderr.write(self.style.ERROR(f"Missing columns in CSV: {', '.join(missing_columns)}"))
                return

            for row in reader:
                profile = Profile(
                    name=row['name'],
                    instagram=row.get('instagram', ''),
                    twitter=row.get('twitter', '')
                )

                image_url = row.get('image_url', '')
                if image_url:
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        profile.image.save(
                            image_url.split('/')[-1],
                            ContentFile(response.content),
                            save=False
                        )
                    else:
                        self.stderr.write(self.style.WARNING(f"Couldn't retrieve image for {profile.name}"))

                profile.save()
                self.stdout.write(self.style.SUCCESS(f"Added profile: {profile.name}"))
