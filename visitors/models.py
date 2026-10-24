
from django.db import models


PURPOSE_CHOICES = [
    ("Official Meeting", "Official Meeting"),
    ("Academic Consultation", "Academic Consultation"),
    ("Document Submission", "Document Submission"),
    ("Document Request", "Document Request"),
    ("Enrollment Inquiry", "Enrollment Inquiry"),
    ("Student Visit", "Student Visit"),
    ("Business Transaction", "Business Transaction"),
    ("Parent-Teacher Meeting", "Parent-Teacher Meeting"),
    ("Others", "Others"),
]


class Visitor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20)

    purpose = models.TextField(choices=PURPOSE_CHOICES)

    time_in = models.DateTimeField(auto_now_add=True)

    id_document = models.FileField(
        upload_to="visitor_ids/",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
