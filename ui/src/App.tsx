import { RouterProvider } from 'react-router-dom';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/toaster';
import { router } from '@/routes';

function App() {
  return (
    <ThemeProvider>
      <Toaster>
        <RouterProvider router={router} />
      </Toaster>
    </ThemeProvider>
  );
}

export default App;
