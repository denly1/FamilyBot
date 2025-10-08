import { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface Story {
  id: number;
  title: string;
  content: {
    subtitle?: string;
    items?: string[];
  };
  avatar: string;
  image?: string;
}

const stories: Story[] = [
  {
    id: 1,
    title: 'Работа в проекте',
    avatar: '/Кружок1.jpg',
    image: '/ФонВкружок1.jpg',
    content: {
      subtitle: undefined,
      items: []
    }
  },
  {
    id: 2,
    title: 'О НАС',
    avatar: '/Кружок2.jpg',
    content: {
      subtitle: 'THE FAMILY',
      items: [
        'THE FAMILY — современное молодёжное движение и профессиональная команда, которая устраивает самые яркие вечеринки для подростков в Москве.',
        'Каждое наше событие — это уникальный опыт, о котором хочется рассказывать снова и снова.',
        'За нашими плечами — сотни незабываемых мероприятий и тысячи счастливых гостей!',
        'Мы не просто организовываем ивенты — мы путеводитель ваших эмоций, которые остаются надолго.'
      ]
    }
  },
  {
    id: 3,
    title: 'МЕДИА STAFF',
    avatar: '/Кружок3.jpg',
    content: {
      subtitle: 'Медиа-staff',
      items: [
        'TikTok, Reels и вирусный контент, который заходит!',
        '— Создаем тренды.',
        '— Снимаем и монтируем видео.',
        '— Придумываем идеи, которые видят тысячи.',
        'Хочешь стать частью нашей media команды? Пиши нам!'
      ]
    }
  }
];

const STORY_DURATION = 15000;

export default function Stories() {
  const [activeStoryIndex, setActiveStoryIndex] = useState<number | null>(null);
  const [progress, setProgress] = useState(0);
  const [touchStart, setTouchStart] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const openStory = (index: number) => {
    setActiveStoryIndex(index);
    setProgress(0);
  };

  const closeStory = () => {
    setActiveStoryIndex(null);
    setProgress(0);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const nextStory = () => {
    if (activeStoryIndex === null) return;

    if (activeStoryIndex < stories.length - 1) {
      setActiveStoryIndex(activeStoryIndex + 1);
      setProgress(0);
    } else {
      closeStory();
    }
  };

  const prevStory = () => {
    if (activeStoryIndex === null) return;

    if (activeStoryIndex > 0) {
      setActiveStoryIndex(activeStoryIndex - 1);
      setProgress(0);
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStart(e.touches[0].clientX);
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const touchEnd = e.changedTouches[0].clientX;
    const diff = touchStart - touchEnd;

    if (Math.abs(diff) > 50) {
      if (diff > 0) {
        nextStory();
      } else {
        prevStory();
      }
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    const clickX = e.clientX;
    const screenWidth = window.innerWidth;

    if (clickX < screenWidth / 3) {
      prevStory();
    } else if (clickX > (screenWidth * 2) / 3) {
      nextStory();
    }
  };

  useEffect(() => {
    if (activeStoryIndex !== null) {
      setProgress(0);

      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }

      intervalRef.current = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            nextStory();
            return 0;
          }
          return prev + (100 / (STORY_DURATION / 50));
        });
      }, 50);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [activeStoryIndex]);

  const currentStory = activeStoryIndex !== null ? stories[activeStoryIndex] : null;
  const isFirstStory = currentStory?.id === 1;

  return (
    <>
      <div className="flex gap-3 p-4 overflow-x-auto">
        {stories.map((story, index) => (
          <div
            key={story.id}
            onClick={() => openStory(index)}
            className="flex flex-col items-center gap-2 cursor-pointer flex-shrink-0"
          >
            <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-cyan-500 to-fuchsia-500 p-1 flex items-center justify-center">
              <div className="w-full h-full rounded-full overflow-hidden border-2 border-black/40">
                <img
                  src={story.avatar}
                  alt={story.title}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </div>
            </div>
            <span className="text-xs text-white font-medium">{story.title}</span>
          </div>
        ))}
      </div>

      {activeStoryIndex !== null && currentStory && (
        <div
          className="fixed inset-0 z-50 bg-gradient-to-br from-[#0b1220] via-[#1a1640] to-[#2b0f4f]"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          onClick={handleClick}
        >
          <div className="relative w-full h-full">
            <div className="absolute top-2 left-2 right-2 flex gap-1 z-10">
              {stories.map((_, index) => (
                <div key={index} className="flex-1 h-1 bg-white/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-white transition-all duration-100"
                    style={{
                      width: index < activeStoryIndex ? '100%' : index === activeStoryIndex ? `${progress}%` : '0%'
                    }}
                  />
                </div>
              ))}
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                closeStory();
              }}
              className="absolute top-4 right-4 z-20 text-white"
            >
              <X size={32} />
            </button>

            <div
              className={`w-full h-full flex flex-col ${isFirstStory ? 'items-start' : 'items-center'} justify-center p-6 sm:p-8 text-white`}
            >
              <div
                className={`w-full max-w-2xl ${isFirstStory ? 'sm:max-w-3xl lg:max-w-5xl' : 'mx-auto'}`}
              >
                {currentStory.image && (
                  <div
                    className={`mb-8 rounded-3xl overflow-hidden border border-white/10 shadow-2xl ${isFirstStory ? '' : 'mx-auto'}`}
                    style={isFirstStory ? { width: 'min(90vw, 1200px)' } : undefined}
                  >
                    <img
                      src={currentStory.image}
                      alt={currentStory.title}
                      className={`w-full object-cover ${isFirstStory ? 'h-auto' : 'h-full'}`}
                      loading="lazy"
                    />
                  </div>
                )}
                {currentStory.content.subtitle && (
                  <h2 className="text-lg sm:text-xl font-black mb-3 text-center bg-gradient-to-r from-cyan-400 via-purple-400 to-fuchsia-400 bg-clip-text text-transparent drop-shadow-2xl animate-pulse px-2">
                    {currentStory.content.subtitle}
                  </h2>
                )}
                {currentStory.content.items && currentStory.content.items.length > 0 && (
                  <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-2 px-2">
                    {currentStory.content.items.map((item, index) => (
                      <div
                        key={index}
                        className="group relative bg-gradient-to-br from-white/15 via-white/10 to-white/5 backdrop-blur-md rounded-lg p-3 border border-white/30 shadow-xl hover:scale-[1.01] transition-all duration-300"
                      >
                        {/* Декоративный градиент фон */}
                        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 via-purple-500/10 to-fuchsia-500/10 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        
                        <div className="relative flex items-start gap-2">
                          <span className="flex-shrink-0 w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-gradient-to-br from-cyan-500 via-purple-500 to-fuchsia-500 flex items-center justify-center text-xs font-bold text-white shadow-lg">
                            {index + 1}
                          </span>
                          <p className="text-xs sm:text-sm leading-relaxed text-white/95 font-medium break-words">
                            {item}
                          </p>
                        </div>
                        
                        {/* Декоративный блик */}
                        <div className="absolute top-0 right-0 w-10 h-10 bg-gradient-to-br from-white/20 to-transparent rounded-full blur-xl opacity-50" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
