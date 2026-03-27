import { useEffect, useState } from 'react';
import { cn } from 'lib/utils';
import { appConfig } from 'config/environment';

interface AuthenticatedImageProps {
  src: string;
  token: string | null;
  tokenType?: string;
  alt?: string;
  className?: string;
  fallback?: React.ReactNode;
}

export function AuthenticatedImage({
  src,
  token,
  tokenType = 'Bearer',
  alt,
  className,
  fallback,
}: AuthenticatedImageProps) {
  const [imageSrc, setImageSrc] = useState<string | undefined>();
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!src || !token) {
      setError(true);
      return;
    }

    let objectUrl: string | undefined;
    setError(false);

    const fullUrl = src.startsWith('http')
      ? src
      : `${appConfig.apiBaseUrl}${src}`;

    fetch(fullUrl, {
      headers: { Authorization: `${tokenType} ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch image');
        return res.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setImageSrc(objectUrl);
      })
      .catch(() => setError(true));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, token, tokenType]);

  if (error || !imageSrc) {
    if (fallback) return <>{fallback}</>;
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-full bg-muted text-muted-foreground text-sm font-medium',
          className
        )}
      >
        {alt?.[0]?.toUpperCase() || '?'}
      </div>
    );
  }

  return (
    <img
      src={imageSrc}
      alt={alt || ''}
      className={cn('object-cover', className)}
    />
  );
}

export default AuthenticatedImage;
