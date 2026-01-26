import { Box, Typography } from '@mui/material';
import StandaloneAppsManager from '../components/StandaloneAppsManager';

import '../styles/page.css';

const AppsPage = () => {
  return (
    <Box component="section" className="page-container">
      <Box className="page-header">
        <Box>
          <Typography variant="h4" component="h1" className="page-title">
            Standalone App Templates
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Upload pre-signed app templates for each platform. These will be bundled with book content.
          </Typography>
        </Box>
      </Box>

      <StandaloneAppsManager />
    </Box>
  );
};

export default AppsPage;
