'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ExternalLink, RefreshCw, MapPin, Briefcase, DollarSign, Calendar } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface Job {
  job_id: string
  title: string
  company: string
  location: string
  description: string
  apply_link: string
  employment_type?: string
  salary_min?: number
  salary_max?: number
  salary_currency?: string
  salary_period?: string
  posted_date?: string
  is_remote?: boolean
  experience_level?: number
  logo?: string
  publisher?: string
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [lastFetchTime, setLastFetchTime] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchCachedJobs = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/jobs/cached')
      const data = await response.json()

      if (data.success) {
        setJobs(data.jobs)
        setLastFetchTime(data.last_fetch_time)
      }
    } catch (error) {
      console.error('Error fetching jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  const triggerScrape = async () => {
    setIsRefreshing(true)
    try {
      const response = await fetch('http://localhost:8000/api/jobs/scrape', {
        method: 'POST',
      })
      const data = await response.json()

      if (data.success) {
        setJobs(data.jobs)
        setLastFetchTime(new Date().toISOString())
      }
    } catch (error) {
      console.error('Error scraping jobs:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchCachedJobs()

    // Refresh cached jobs every 5 minutes
    const interval = setInterval(fetchCachedJobs, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const formatSalary = (job: Job) => {
    if (!job.salary_min && !job.salary_max) return 'Not specified'

    const currency = job.salary_currency || 'USD'
    const period = job.salary_period || 'year'

    if (job.salary_min && job.salary_max) {
      return `${currency} ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()} / ${period}`
    } else if (job.salary_min) {
      return `${currency} ${job.salary_min.toLocaleString()}+ / ${period}`
    } else if (job.salary_max) {
      return `Up to ${currency} ${job.salary_max.toLocaleString()} / ${period}`
    }

    return 'Not specified'
  }

  const formatPostedDate = (dateString?: string) => {
    if (!dateString) return 'Recently'
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return 'Recently'
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">Loading jobs...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Job Board</h1>
            <p className="text-muted-foreground">
              Browse the latest job opportunities scraped from the web
            </p>
            {lastFetchTime && (
              <p className="text-sm text-muted-foreground mt-2">
                Last updated: {formatPostedDate(lastFetchTime)}
              </p>
            )}
          </div>
          <Button
            onClick={triggerScrape}
            disabled={isRefreshing}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh Jobs'}
          </Button>
        </div>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-12 border rounded-lg">
          <Briefcase className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-lg font-semibold mb-2">No jobs found</h3>
          <p className="text-muted-foreground mb-4">
            Click "Refresh Jobs" to scrape the latest job postings
          </p>
          <Button onClick={triggerScrape} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh Jobs'}
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[300px]">Job Title</TableHead>
                <TableHead className="w-[200px]">Company</TableHead>
                <TableHead className="w-[180px]">Location</TableHead>
                <TableHead className="w-[150px]">Type</TableHead>
                <TableHead className="w-[200px]">Salary</TableHead>
                <TableHead className="w-[130px]">Posted</TableHead>
                <TableHead className="w-[100px]">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.job_id}>
                  <TableCell className="font-medium">
                    <div>
                      <div className="font-semibold">{job.title}</div>
                      {job.is_remote && (
                        <span className="inline-flex items-center gap-1 text-xs text-blue-600 mt-1">
                          <MapPin className="h-3 w-3" />
                          Remote
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {job.logo && (
                        <img
                          src={job.logo}
                          alt={job.company}
                          className="h-6 w-6 rounded"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none'
                          }}
                        />
                      )}
                      <span>{job.company}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <MapPin className="h-4 w-4" />
                      {job.location || 'Not specified'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm">
                      <Briefcase className="h-4 w-4" />
                      {job.employment_type || 'Not specified'}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <DollarSign className="h-4 w-4" />
                      <span className="text-xs">{formatSalary(job)}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      {formatPostedDate(job.posted_date)}
                    </div>
                  </TableCell>
                  <TableCell>
                    {job.apply_link ? (
                      <Button
                        asChild
                        variant="outline"
                        size="sm"
                        className="gap-2"
                      >
                        <a
                          href={job.apply_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Apply
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    ) : (
                      <span className="text-sm text-muted-foreground">N/A</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="mt-6 p-4 bg-muted/50 rounded-lg">
        <p className="text-sm text-muted-foreground">
          <strong>Note:</strong> Jobs are automatically scraped every hour. You can also manually refresh the list using the "Refresh Jobs" button.
          The backend uses the JSearch API to fetch real-time job listings.
        </p>
      </div>
    </div>
  )
}
