const normalizeScheme = (value: string) => {
  if (!value) {
    return 'Bearer';
  }

  return value.toLowerCase() === 'bearer' ? 'Bearer' : value;
};

export const buildAuthHeaders = (token: string, tokenType: string = 'Bearer') => ({
  Authorization: `${normalizeScheme(tokenType)} ${token}`
});
