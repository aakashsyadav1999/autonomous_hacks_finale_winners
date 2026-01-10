"""
Django Management Command: cleanup_unsubmitted_complaints

This command deletes CivicComplaint records that were captured but never
submitted (is_submit=False) on the current day. Designed to run as a
daily cron job at 11:55 PM.

Usage:
    python manage.py cleanup_unsubmitted_complaints

Cron Schedule:
    55 23 * * * cd /path/to/project && python manage.py cleanup_unsubmitted_complaints
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time
from user_portal.models import CivicComplaint


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to clean up unsubmitted civic complaints.
    
    Deletes all CivicComplaint records where:
    - is_submit = False (not submitted by user)
    - created_at is from today (midnight to 11:55 PM)
    
    This prevents storage bloat from abandoned photo captures.
    """
    
    help = 'Delete unsubmitted civic complaints from today'
    
    def add_arguments(self, parser):
        """
        Add command-line arguments.
        
        --dry-run: Show what would be deleted without actually deleting
        """
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
    
    def handle(self, *args, **options):
        """
        Execute the cleanup command.
        
        Args:
            options: Command options (dry_run flag)
        """
        is_dry_run = options['dry_run']
        
        # Get current date in Asia/Kolkata timezone
        now = timezone.now()
        today_start = timezone.make_aware(
            datetime.combine(now.date(), time.min)
        )
        today_end = timezone.make_aware(
            datetime.combine(now.date(), time.max)
        )
        
        # Query unsubmitted complaints from today
        unsubmitted_complaints = CivicComplaint.objects.filter(
            is_submit=False,
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        
        count = unsubmitted_complaints.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No unsubmitted complaints found for today.')
            )
            logger.info('Cleanup: No unsubmitted complaints found')
            return
        
        # Display what will be deleted
        self.stdout.write(
            self.style.WARNING(f'Found {count} unsubmitted complaints from today:')
        )
        
        for complaint in unsubmitted_complaints[:10]:  # Show first 10
            self.stdout.write(
                f'  - ID: {complaint.id}, Area: {complaint.area}, '
                f'Created: {complaint.created_at.strftime("%H:%M:%S")}'
            )
        
        if count > 10:
            self.stdout.write(f'  ... and {count - 10} more')
        
        if is_dry_run:
            self.stdout.write(
                self.style.WARNING('\n[DRY RUN] No complaints were deleted.')
            )
            logger.info(f'Cleanup dry run: Would delete {count} complaints')
            return
        
        # Confirm deletion in interactive mode
        if not options.get('no_input'):
            confirm = input(f'\nDelete {count} complaints? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR('Cleanup cancelled.'))
                return
        
        # Delete complaints
        deleted_count, _ = unsubmitted_complaints.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully deleted {deleted_count} unsubmitted complaints.'
            )
        )
        
        logger.info(
            f'Cleanup completed: Deleted {deleted_count} unsubmitted complaints '
            f'from {now.date()}'
        )
        
        # Log storage savings estimate
        self.stdout.write(
            self.style.SUCCESS(
                f'Estimated storage freed: ~{deleted_count * 2}MB '
                f'(assuming avg 2MB per photo)'
            )
        )
