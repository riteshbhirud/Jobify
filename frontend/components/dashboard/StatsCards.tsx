import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface StatsCardsProps {
  stats: {
    today: number
    thisWeek: number
    total: number
    interviews: number
  }
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    { title: 'Today', value: stats.today, subtitle: 'applied', icon: '📅' },
    { title: 'This Week', value: stats.thisWeek, subtitle: 'applied', icon: '📊' },
    { title: 'Total', value: stats.total, subtitle: 'applied', icon: '🎯' },
    { title: 'Interviews', value: stats.interviews, subtitle: 'scheduled', icon: '🎤' },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.title}
            </CardTitle>
            <span className="text-2xl">{card.icon}</span>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{card.value}</div>
            <p className="text-xs text-muted-foreground mt-1">{card.subtitle}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
