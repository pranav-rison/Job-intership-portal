from django.shortcuts import render

def apply_for_job(request, job_id):
    # For now, just render the template with the job_id
    return render(request, "application/apply.html", {"job_id": job_id})