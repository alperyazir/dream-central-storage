import { useEffect, useState } from 'react';
import { Avatar, AvatarProps } from '@mui/material';

interface AuthenticatedImageProps extends Omit<AvatarProps, 'src'> {
  src: string;
  token: string | null;
  tokenType?: string;
  fallback?: React.ReactNode;
}

const AuthenticatedImage = ({ 
  src, 
  token, 
  tokenType = 'Bearer', 
  fallback,
  ...avatarProps 
}: AuthenticatedImageProps) => {
  const [imageSrc, setImageSrc] = useState<string | undefined>(undefined);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!src || !token) {
      setImageSrc(undefined);
      return;
    }

    const fetchImage = async () => {
      try {
        const response = await fetch(src, {
          headers: {
            Authorization: `${tokenType} ${token}`,
          },
        });

        if (!response.ok) {
          setError(true);
          return;
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        setImageSrc(objectUrl);
      } catch (err) {
        console.error('Failed to fetch image:', err);
        setError(true);
      }
    };

    fetchImage();

    // Cleanup object URL on unmount
    return () => {
      if (imageSrc) {
        URL.revokeObjectURL(imageSrc);
      }
    };
  }, [src, token, tokenType]);

  if (error || !imageSrc) {
    return <Avatar {...avatarProps}>{fallback}</Avatar>;
  }

  return <Avatar {...avatarProps} src={imageSrc} />;
};

export default AuthenticatedImage;
