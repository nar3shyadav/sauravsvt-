import { Component, inject, OnInit } from '@angular/core';
import { JobService, Job } from '../../../core/services/job.service';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-job-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './job-detail.component.html',
  styleUrl: './job-detail.component.css',
})
export class JobDetailComponent implements OnInit {
  jobService = inject(JobService);
  authService = inject(AuthService);
  route = inject(ActivatedRoute);

  job: Job | null = null;
  loading = true;
  error = '';
  currentUser$ = this.authService.currentUser$;

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadJob(id);
    } else {
      this.error = 'Invalid Job ID';
      this.loading = false;
    }
  }

  loadJob(id: string) {
    this.jobService.getJobById(id).subscribe({
      next: (data) => {
        this.job = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load job details.';
        this.loading = false;
      }
    });
  }

  applyJob() {
    // Implement application logic here (e.g. open modal or redirect to apply form)
    // For now, simple alert or log
    alert('Application feature coming soon!'); // Placeholder
    // Todo: Create Apply Component
  }
}
