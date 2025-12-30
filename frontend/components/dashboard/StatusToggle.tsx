'use client'

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"

interface StatusToggleProps {
  isActive: boolean
  onToggle: (active: boolean) => Promise<void>
}

export function StatusToggle({ isActive, onToggle }: StatusToggleProps) {
  const [loading, setLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const handleToggle = async () => {
    // If turning ON, show confirmation
    if (!isActive) {
      setShowConfirm(true)
    } else {
      // Turning OFF is immediate
      setLoading(true)
      try {
        await onToggle(false)
      } finally {
        setLoading(false)
      }
    }
  }

  const confirmActivate = async () => {
    setLoading(true)
    try {
      await onToggle(true)
      setShowConfirm(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-2">
      <CardHeader>
        <CardTitle>Automation Status</CardTitle>
      </CardHeader>
      <CardContent>
        {!showConfirm ? (
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="automation-toggle" className="text-base font-medium cursor-pointer">
                {isActive ? (
                  <span className="flex items-center">
                    <span className="inline-block w-3 h-3 bg-secondary rounded-full mr-2 animate-pulse" />
                    ACTIVE - Applying to matching jobs automatically
                  </span>
                ) : (
                  <span className="flex items-center">
                    <span className="inline-block w-3 h-3 bg-destructive rounded-full mr-2" />
                    PAUSED - No applications being submitted
                  </span>
                )}
              </Label>
              <p className="text-sm text-muted-foreground">
                {isActive
                  ? "Your automation is running. We'll apply to jobs that match your preferences."
                  : "Turn on automation to start applying to jobs automatically."}
              </p>
            </div>
            <Switch
              id="automation-toggle"
              checked={isActive}
              onCheckedChange={handleToggle}
              disabled={loading}
              className="scale-125"
            />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-primary/10 border border-primary/20 rounded-md p-4">
              <p className="font-medium mb-2">Are you sure?</p>
              <p className="text-sm text-muted-foreground">
                We'll start applying to matching jobs immediately. You can pause anytime.
              </p>
            </div>
            <div className="flex space-x-3">
              <Button onClick={confirmActivate} disabled={loading} className="flex-1">
                {loading ? 'Activating...' : 'Yes, Activate'}
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowConfirm(false)}
                disabled={loading}
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
