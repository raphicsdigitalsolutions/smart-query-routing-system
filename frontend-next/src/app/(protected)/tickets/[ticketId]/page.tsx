import { TicketDetail } from '@/components/tickets/TicketDetail';

interface TicketDetailPageProps {
  params: Promise<{ ticketId: string }>;
}

export default async function TicketDetailPage({ params }: TicketDetailPageProps) {
  const { ticketId } = await params;
  return <TicketDetail ticketId={ticketId} />;
}
