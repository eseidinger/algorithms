import {
  Alert,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { createExecution } from '../../api/executions'
import {
  FIBONACCI_SCENARIO_VERSION_ID,
  getFibonacciScenario,
} from '../../api/scenarios'

export default function FibonacciPage() {
  const navigate = useNavigate()
  const scenario = useQuery({
    queryKey: ['scenario-version', FIBONACCI_SCENARIO_VERSION_ID],
    queryFn: ({ signal }) => getFibonacciScenario(signal),
    retry: 1,
  })

  const execution = useMutation({
    mutationFn: createExecution,
    retry: false,
    onSuccess: (created) => navigate(`/executions/${created.id}`),
  })

  if (scenario.isPending) {
    return <CircularProgress aria-label="Loading scenario" />
  }

  if (scenario.isError) {
    return (
      <Alert severity="error">Could not load the Fibonacci scenario.</Alert>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">
        Fibonacci
      </Typography>
      <Typography>{scenario.data.name}</Typography>
      <Typography>Input: n = {scenario.data.input.n}</Typography>

      <Button
        variant="contained"
        disabled={execution.isPending}
        onClick={() => execution.mutate(scenario.data.id)}
      >
        {execution.isPending ? 'Starting…' : 'Run Fibonacci'}
      </Button>

      {execution.isError && (
        <Alert severity="error">Could not confirm the execution.</Alert>
      )}
    </Stack>
  )
}
