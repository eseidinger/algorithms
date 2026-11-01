import { AppBar, Container, Toolbar, Typography } from '@mui/material'
import { Route, Routes } from 'react-router'
import CatalogPage from './features/catalog/CatalogPage'
import FibonacciPage from './features/fibonacci/FibonacciPage'

export default function App() {
  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div">
            Algorithm Lab
          </Typography>
        </Toolbar>
      </AppBar>

      <Container component="main" maxWidth="lg" sx={{ py: 4 }}>
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/showcases/K01" element={<FibonacciPage />} />
          <Route path="*" element={<Typography>Page not found.</Typography>} />
        </Routes>
      </Container>
    </>
  )
}
