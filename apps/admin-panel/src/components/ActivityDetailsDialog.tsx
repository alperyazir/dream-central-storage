import {
  Dialog,
  DialogTitle,
  DialogContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  IconButton,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

interface ActivityDetailsDialogProps {
  open: boolean;
  onClose: () => void;
  bookTitle: string;
  activityCount?: number;
  activityDetails?: Record<string, number>;
}

const ActivityDetailsDialog = ({
  open,
  onClose,
  bookTitle,
  activityCount,
  activityDetails,
}: ActivityDetailsDialogProps) => {
  const hasDetails = activityDetails && Object.keys(activityDetails).length > 0;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Activity Details - {bookTitle}</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body1" color="text.secondary">
            Total Activities: <strong>{activityCount || 0}</strong>
          </Typography>
        </Box>

        {hasDetails ? (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><strong>Activity Type</strong></TableCell>
                  <TableCell align="right"><strong>Count</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(activityDetails)
                  .sort(([, a], [, b]) => b - a)
                  .map(([activityType, count]) => (
                    <TableRow key={activityType}>
                      <TableCell>{activityType}</TableCell>
                      <TableCell align="right">{count}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No activity details available for this book.
          </Typography>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ActivityDetailsDialog;
