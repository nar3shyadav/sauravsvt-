import { Component, inject, OnInit } from '@angular/core';
import { JobService, Job } from '../../../core/services/job.service';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';

@Component({
  selector: 'app-job-list',
  standalone: true,
  imports: [CommonModule, RouterLink, ReactiveFormsModule],
  templateUrl: './job-list.component.html',
  styleUrl: './job-list.component.css',
})
export class JobListComponent implements OnInit {
  jobService = inject(JobService);
  fb = inject(FormBuilder);

  jobs: Job[] = [];
  loading = true;
  error = '';

  filterForm: FormGroup;

  constructor() {
    this.filterForm = this.fb.group({
      title: [''],
      location: ['']
    });
  }

  ngOnInit() {
    this.loadJobs();
  }

  loadJobs() {
    this.loading = true;
    const filters = this.filterForm.value;
    // Remove empty filters
    const activeFilters: any = {};
    if (filters.title) activeFilters.title = filters.title;
    if (filters.location) activeFilters.location = filters.location;

    this.jobService.getJobs(activeFilters).subscribe({
      next: (data) => {
        this.jobs = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load jobs.';
        this.loading = false;
      }
    });
  }

  onSearch() {
    this.loadJobs();
  }
}
