import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from notices.models import Community, Profile

class Command(BaseCommand):
    help = 'Bulk imports students from a specified CSV file'

    # This allows you to pass the filename when you run the command
    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file (e.g., students.csv)')

    def handle(self, *args, **kwargs):
        file_path = kwargs['csv_file']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ Error: Could not find '{file_path}'."))
            return

        self.stdout.write(self.style.WARNING(f"Starting Bulk Import from {file_path}...\n"))
        
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            success_count = 0
            skip_count = 0
            
            for row in reader:
                username = row['Username'].strip()
                email = row['Email'].strip()
                dept = row['Department'].strip()
                community_name = row['Community'].strip()

                # 1. Community
                community, c_created = Community.objects.get_or_create(
                    name=community_name, 
                    defaults={"department": dept}
                )
                
                # 2. User
                user, u_created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': email}
                )
                
                if u_created:
                    user.set_password("password123") 
                    user.save()
                    
                    # 3. Profile Linkage
                    profile = user.profile
                    profile.department = dept
                    profile.community = community
                    profile.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"✅ Added: {username} -> {community_name}"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.NOTICE(f"⏩ Skipped: {username} (Already exists)"))
                    skip_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"\n🎉 Import Complete! Added: {success_count} | Skipped: {skip_count}"))