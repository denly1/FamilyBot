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
    try {
      const data = await getPosters();
      console.log('API response:', data);
      
      setPosters(data);
      // Показываем последнюю афишу (самую новую)
      if (data.length > 0) {
        setCurrentIndex(data.length - 1);
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
  // Последняя афиша (самая новая) для кнопки билета
  const latestPoster = posters.length > 0 ? posters[posters.length - 1] : null;

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
            <div 
              className="px-4 pb-28"
              onTouchStart={handleTouchStart}
              onTouchMove={handleTouchMove}
              onTouchEnd={handleTouchEnd}
            >
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

              {/* Фото афиши */}
              <div className="relative rounded-3xl overflow-hidden shadow-2xl mb-6">
                <img
                  src={
                    (currentPoster as any).photo_url?.startsWith('/posters/')
                      ? (currentPoster as any).photo_url
                      : `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${(currentPoster as any).photo_url || `/photo/${currentPoster.file_id}`}`
                  }
                  alt="Афиша"
                  className="w-full h-auto object-cover"
                  onError={(e) => {
                    console.error('Failed to load image:', e);
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

        {/* Кнопка билета - всегда для последней (актуальной) афиши */}
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 via-black/70 to-transparent backdrop-blur-sm">
          <a
            href={latestPoster?.ticket_url || 'https://clck.ru/3PS3DG'}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full py-4 px-6 bg-gradient-to-r from-blue-500 via-indigo-600 to-purple-600 text-white font-bold text-lg rounded-xl hover:shadow-lg hover:shadow-indigo-500/30 hover:scale-[1.02] active:scale-95 transition-all duration-300 text-center transform-gpu"
          >
            Купить билет
          </a>
        </div>
      </main>
    </div>
  );
}

export default App;
