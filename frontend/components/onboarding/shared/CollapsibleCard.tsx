'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Trash2 } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface CollapsibleCardProps {
  title: string
  subtitle?: string
  defaultExpanded?: boolean
  onDelete?: () => void
  canDelete?: boolean
  children: React.ReactNode
  isNew?: boolean
}

export function CollapsibleCard({
  title,
  subtitle,
  defaultExpanded = false,
  onDelete,
  canDelete = true,
  children,
  isNew = false,
}: CollapsibleCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded || isNew)

  return (
    <motion.div
      initial={isNew ? { opacity: 0, y: -10 } : false}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10, height: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Card className="overflow-hidden">
        <CardHeader
          className="cursor-pointer hover:bg-muted/50 transition-colors py-4"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ rotate: isExpanded ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                </motion.div>
                <h3 className="font-medium truncate">
                  {title || 'New Entry'}
                </h3>
              </div>
              {subtitle && !isExpanded && (
                <p className="text-sm text-muted-foreground ml-6 truncate">
                  {subtitle}
                </p>
              )}
            </div>
            {canDelete && onDelete && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete()
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <CardContent className="pt-0 pb-6">
                {children}
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  )
}
