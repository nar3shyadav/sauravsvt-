import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Job {
  _id: string;
  company_name: string;
  title: string;
  description: string;
  location: string;
  work_type: string;
  salary_range?: string;
  requirements?: string;
  views: number;
  date_posted: string;
  posted_by: string;
}

@Injectable({
  providedIn: 'root',
})
export class JobService {
  private http = inject(HttpClient);
  // Hardcoded for now, should use environment
  private readonly BASE_URL = 'http://localhost:5002/jobs';

  getJobs(filters?: { title?: string, location?: string }): Observable<Job[]> {
    let params: any = {};
    if (filters?.title) params.title = filters.title;
    if (filters?.location) params.location = filters.location;
    return this.http.get<Job[]>(this.BASE_URL, { params });
  }

  getJobById(id: string): Observable<Job> {
    return this.http.get<Job>(`${this.BASE_URL}/${id}`);
  }

  createJob(job: Partial<Job>): Observable<Job> {
    return this.http.post<Job>(this.BASE_URL, job);
  }

  deleteJob(id: string): Observable<any> {
    return this.http.delete(`${this.BASE_URL}/${id}`);
  }

  // applications related methods could be here or in separate service
}
