from django.shortcuts import render

def apply_for_job(request, job_id=None):
    return render(request, "application/apply.html", {"job_id": job_id})