import {
  Alert,
  Button,
  Card,
  CardActions,
  CardContent,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router'
import { getShowcases } from '../../api/catalog'

export default function CatalogPage() {
  const query = useQuery({
    queryKey: ['showcases'],
    queryFn: ({ signal }) => getShowcases(signal),
    retry: 1,
  })

  return (
    <>
      <Typography variant="h4" component="h1" gutterBottom>
        Algorithm Catalog
      </Typography>

      {query.isPending && <CircularProgress aria-label="Loading catalog" />}

      {query.isError && (
        <Alert severity="error">
          Could not load the catalog. Please try again later.
        </Alert>
      )}

      {query.isSuccess && query.data.length === 0 && (
        <Typography>No showcases available.</Typography>
      )}

      {query.isSuccess && (
        <Stack spacing={2}>
          {query.data.map((showcase) => (
            <Card key={showcase.id}>
              <CardContent>
                <Typography variant="h6" component="h2">
                  {showcase.name}
                </Typography>
                <Typography>{showcase.description}</Typography>
              </CardContent>
              {showcase.id === 'K01' && (
                <CardActions>
                  <Button component={RouterLink} to="/showcases/K01">
                    Open showcase
                  </Button>
                </CardActions>
              )}
            </Card>
          ))}
        </Stack>
      )}
    </>
  )
}
