import { ExternalLink } from 'lucide-react';

interface EventPosterProps {
  title: string;
  subtitle: string;
  date: string;
  time: string;
  location: string;
  imageUrl: string;
  ticketUrl: string;
}

export default function EventPoster({
  title,
  subtitle,
  date,
  time,
  location,
  imageUrl,
  ticketUrl
}: EventPosterProps) {
  return (
    <div className="px-4 pb-28">
      <div className="relative rounded-3xl overflow-hidden shadow-2xl">
        <img
          src={imageUrl}
          alt={title}
          className="w-full h-auto object-cover"
        />
      </div>

      <div className="mt-6 space-y-4">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-black text-white tracking-tight drop-shadow-lg">
            {title}
          </h1>
          <p className="text-xl text-white/90 font-medium drop-shadow-md">
            {subtitle}
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 text-white/80 text-sm">
          <span>{date}</span>
          <span>•</span>
          <span>{time}</span>
        </div>

        <div className="text-familycenter">
          <p className="text-white/70 text-sm">{location}</p>
        </div>

        {ticketUrl && (
          <div className="pt-2 flex justify-center">
            <a
              href={ticketUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full text-sm font-medium transition-colors"
            >
              Купить билет
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
