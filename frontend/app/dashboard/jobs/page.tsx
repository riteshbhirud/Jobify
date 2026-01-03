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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
  source?: string
}

interface ApiStats {
  [key: string]: {
    count: number
    last_fetch: string | null
    status: string
  }
}

type SortOption = 'date-desc' | 'date-asc' | 'salary-desc' | 'salary-asc' | 'none'

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [lastFetchTime, setLastFetchTime] = useState<string | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [apiStats, setApiStats] = useState<ApiStats>({})
  const [sortBy, setSortBy] = useState<SortOption>('date-desc')
  const [currentPage, setCurrentPage] = useState(1)
  const JOBS_PER_PAGE = 50

  const fetchCachedJobs = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/jobs/cached')
      const data = await response.json()

      if (data.success) {
        setJobs(data.jobs)
        setLastFetchTime(data.last_fetch_time)
        if (data.sources) {
          setApiStats(data.sources)
        }
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
        setCurrentPage(1) // Reset to first page
        if (data.sources) {
          setApiStats(data.sources)
        }
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

  // Reset to first page when sort changes
  useEffect(() => {
    setCurrentPage(1)
  }, [sortBy])

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
    if (!dateString) return 'Unknown'
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return 'Unknown'
    }
  }

  const filterJobsByTime = (jobs: Job[]) => {
    const fiveHoursAgo = new Date()
    fiveHoursAgo.setHours(fiveHoursAgo.getHours() - 5)

    return jobs.filter(job => {
      if (!job.posted_date) return false // Exclude jobs without posted date

      try {
        const postedDate = new Date(job.posted_date)
        return postedDate >= fiveHoursAgo
      } catch {
        return false
      }
    })
  }

  const getSortedJobs = () => {
    // First filter by time (within last 5 hours)
    const filteredJobs = filterJobsByTime(jobs)
    const jobsCopy = [...filteredJobs]

    switch (sortBy) {
      case 'date-desc':
        return jobsCopy.sort((a, b) => {
          const dateA = a.posted_date ? new Date(a.posted_date).getTime() : 0
          const dateB = b.posted_date ? new Date(b.posted_date).getTime() : 0
          return dateB - dateA // Most recent first
        })

      case 'date-asc':
        return jobsCopy.sort((a, b) => {
          const dateA = a.posted_date ? new Date(a.posted_date).getTime() : 0
          const dateB = b.posted_date ? new Date(b.posted_date).getTime() : 0
          return dateA - dateB // Oldest first
        })

      case 'salary-desc':
        return jobsCopy.sort((a, b) => {
          const salaryA = a.salary_max || a.salary_min || 0
          const salaryB = b.salary_max || b.salary_min || 0
          return salaryB - salaryA // Highest first
        })

      case 'salary-asc':
        return jobsCopy.sort((a, b) => {
          const salaryA = a.salary_max || a.salary_min || 0
          const salaryB = b.salary_max || b.salary_min || 0
          return salaryA - salaryB // Lowest first
        })

      case 'none':
      default:
        return jobsCopy
    }
  }

  const sortedJobs = getSortedJobs()

  // Calculate accurate source stats based on filtered jobs
  const getFilteredSourceStats = () => {
    const stats: { [key: string]: number } = {}

    sortedJobs.forEach(job => {
      const source = (job.source || 'unknown').toLowerCase()
      stats[source] = (stats[source] || 0) + 1
    })

    return stats
  }

  const filteredSourceStats = getFilteredSourceStats()

  // Pagination
  const totalPages = Math.ceil(sortedJobs.length / JOBS_PER_PAGE)
  const startIndex = (currentPage - 1) * JOBS_PER_PAGE
  const endIndex = startIndex + JOBS_PER_PAGE
  const paginatedJobs = sortedJobs.slice(startIndex, endIndex)

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

        {/* Sort Controls */}
        {jobs.length > 0 && (
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-muted/50 rounded-lg">
            {/* Desktop: Buttons */}
            <div className="hidden lg:flex items-center gap-4">
              <span className="text-sm font-medium">Sort by:</span>
              <div className="flex gap-2">
                <Button
                  variant={sortBy === 'date-desc' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('date-desc')}
                >
                  Newest First
                </Button>
                <Button
                  variant={sortBy === 'date-asc' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('date-asc')}
                >
                  Oldest First
                </Button>
                <Button
                  variant={sortBy === 'salary-desc' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('salary-desc')}
                >
                  Highest Salary
                </Button>
                <Button
                  variant={sortBy === 'salary-asc' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('salary-asc')}
                >
                  Lowest Salary
                </Button>
              </div>
            </div>

            {/* Mobile/Tablet: Dropdown */}
            <div className="flex lg:hidden items-center gap-2 w-full sm:w-auto">
              <span className="text-sm font-medium whitespace-nowrap">Sort by:</span>
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortOption)}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="date-desc">Newest First</SelectItem>
                  <SelectItem value="date-asc">Oldest First</SelectItem>
                  <SelectItem value="salary-desc">Highest Salary</SelectItem>
                  <SelectItem value="salary-asc">Lowest Salary</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="text-sm text-muted-foreground">
              Showing <span className="font-semibold text-foreground">{sortedJobs.length}</span> jobs (posted within last 5 hours)
            </div>
          </div>
        )}
      </div>

      {sortedJobs.length === 0 ? (
        <div className="text-center py-12 border rounded-lg">
          <Briefcase className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="text-lg font-semibold mb-2">No recent jobs found</h3>
          <p className="text-muted-foreground mb-4">
            No jobs posted within the last 5 hours. Click "Refresh Jobs" to scrape the latest job postings.
          </p>
          <Button onClick={triggerScrape} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh Jobs'}
          </Button>
        </div>
      ) : (
        <>
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
                {paginatedJobs.map((job) => (
                <TableRow key={job.job_id}>
                  <TableCell className="font-medium">
                    <div>
                      <div className="font-semibold">{job.title}</div>
                      <div className="flex items-center gap-2 mt-1">
                        {job.is_remote && (
                          <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                            <MapPin className="h-3 w-3" />
                            Remote
                          </span>
                        )}
                        {job.source && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-primary/10 text-primary">
                            {job.source}
                          </span>
                        )}
                      </div>
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

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 px-4">
            <div className="text-sm text-muted-foreground">
              Page {currentPage} of {totalPages} • Showing {startIndex + 1}-{Math.min(endIndex, sortedJobs.length)} of {sortedJobs.length} jobs
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </>
      )}

      <div className="mt-6 space-y-4">
        {/* API Source Statistics */}
        {Object.keys(apiStats).length > 0 && (
          <div className="p-4 bg-muted/50 rounded-lg">
            <h3 className="font-semibold mb-3">Data Sources</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(apiStats).map(([source, stats]) => (
                <div key={source} className="flex items-center justify-between p-3 bg-background rounded border">
                  <div>
                    <p className="font-medium capitalize">{source}</p>
                    <p className="text-sm text-muted-foreground">
                      {filteredSourceStats[source] || 0} jobs • Status: {stats.status}
                    </p>
                  </div>
                  {stats.status === 'success' && (
                    <span className="h-2 w-2 bg-green-500 rounded-full"></span>
                  )}
                  {stats.status === 'error' && (
                    <span className="h-2 w-2 bg-red-500 rounded-full"></span>
                  )}
                  {stats.status === 'not_configured' && (
                    <span className="h-2 w-2 bg-yellow-500 rounded-full"></span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Info Note */}
        <div className="p-4 bg-muted/50 rounded-lg">
          <p className="text-sm text-muted-foreground">
            <strong>Note:</strong> Jobs are automatically scraped every hour from multiple sources including JSearch and Findwork.
            Only jobs posted within the last 5 hours are displayed. You can also manually refresh the list using the "Refresh Jobs" button.
            Duplicate listings are automatically filtered out. {sortedJobs.length > 0 && `Displaying ${JOBS_PER_PAGE} jobs per page.`}
          </p>
        </div>
      </div>
    </div>
  )
}
