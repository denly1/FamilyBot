import { useEffect, useState } from 'react';
import Stories from './components/Stories';
import { getPosters, Poster } from './lib/api';

function App() {
  const [posters, setPosters] = useState<Poster[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [touchStart, setTouchStart] = useState(0);
  const [touchEnd, setTouchEnd] = useState(0);

  useEffect(() => {
    fetchPosters();
  }, []);

  async function fetchPosters() {
    console.log('Fetching posters from API...');
    console.log('API URL:', import.meta.env.VITE_API_URL || 'http://localhost:8000');
    try {
      const data = await getPosters();
      console.log('API response:', data);
      
      // Логируем каждую афишу для отладки
      data.forEach((poster, index) => {
        console.log(`Poster ${index}:`, {
          id: poster.id,
          file_id: poster.file_id,
          photo_url: (poster as any).photo_url,
          caption: poster.caption?.substring(0, 30)
        });
      });
      
      setPosters(data);
      // Показываем первую афишу (самую новую, т.к. ORDER BY created_at DESC)
      if (data.length > 0) {
        setCurrentIndex(0);
      }
      console.log('Active posters set:', data);
    } catch (err) {
      console.error('Error in fetchPosters:', err);
      setError('Не удалось загрузить афиши');
    } finally {
      console.log('Loading complete');
      setLoading(false);
    }
  }

  // Обработка свайпа
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStart(e.targetTouches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const handleTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > 50;
    const isRightSwipe = distance < -50;
  
    // Свайп влево - к следующей (более новой)  
    if (isLeftSwipe && currentIndex < posters.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
    // Свайп вправо - к предыдущей (более старой)
    if (isRightSwipe && currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  
    setTouchStart(0);
    setTouchEnd(0);
  };

  const currentPoster = posters[currentIndex] || null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0b1220] via-[#1a1640] to-[#2b0f4f] text-white">
      <main className="relative max-w-md mx-auto min-h-screen overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: 'url(/фон.jpg)' }}
        >
          <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
        </div>

        <div className="relative z-10 pb-24">
          <Stories />

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-20 px-4">
              <p className="text-red-400 text-lg mb-4">❌ {error}</p>
              <button 
                onClick={fetchPosters}
                className="px-6 py-2 bg-cyan-500 hover:bg-cyan-600 rounded-lg transition-colors"
              >
                Попробовать снова
              </button>
            </div>
          ) : currentPoster ? (
            <div className="px-4 pb-28">
              {/* Индикатор количества афиш */}
              {posters.length > 1 && (
                <div className="flex justify-center gap-2 mb-4">
                  {posters.map((_, index) => (
                    <div
                      key={index}
                      className={`h-1.5 rounded-full transition-all duration-300 ${
                        index === currentIndex 
                          ? 'w-8 bg-cyan-500' 
                          : 'w-1.5 bg-white/30'
                      }`}
                    />
                  ))}
                </div>
              )}

              {/* Фото афиши с навигацией свайпом */}
              <div 
                className="relative rounded-3xl overflow-hidden shadow-2xl mb-6"
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
              >
                <img
                  src={(() => {
                    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                    const photoUrl = (currentPoster as any).photo_url || `/photo/${currentPoster.file_id}`;
                    const fullUrl = `${apiUrl}${photoUrl}`;
                    console.log('Loading image:', fullUrl);
                    return fullUrl;
                  })()}
                  alt="Афиша"
                  className="w-full h-auto object-cover"
                  onError={(e) => {
                    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                    const photoUrl = (currentPoster as any).photo_url;
                    console.error('Failed to load image:', {
                      apiUrl,
                      photoUrl,
                      file_id: currentPoster.file_id,
                      fullUrl: `${apiUrl}${photoUrl}`
                    });
                    // Если не удалось загрузить, показываем заглушку
                    e.currentTarget.src = '/фон.jpg';
                  }}
                />
              </div>

              {/* Описание по центру */}
              <div className="mt-6 space-y-4">
                <div className="text-center space-y-2">
                  <div className="text-lg text-white/90 font-medium whitespace-pre-wrap leading-relaxed">
                    {currentPoster.caption || 'Описание отсутствует'}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-20 px-4">
              <p className="text-white/60 text-lg">Скоро здесь появятся новые мероприятия</p>
            </div>
          )}
        </div>

        {/* Кнопка билета - показывается для ТЕКУЩЕЙ афиши */}
        {currentPoster?.ticket_url && (
          <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 via-black/70 to-transparent backdrop-blur-sm z-[9999] pointer-events-auto">
            <a
              href={currentPoster.ticket_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                e.stopPropagation();
                console.log('Кнопка билета нажата! URL:', currentPoster.ticket_url);
              }}
              className="block w-full py-4 px-6 bg-gradient-to-r from-blue-500 via-indigo-600 to-purple-600 text-white font-bold text-lg rounded-xl shadow-2xl shadow-indigo-500/50 active:scale-95 transition-all duration-200 text-center cursor-pointer touch-manipulation"
              style={{ WebkitTapHighlightColor: 'transparent' }}
            >
              🎫 Купить билет
            </a>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
