import { useEffect, lazy, Suspense } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { Header, Footer } from "./components/Layout";
import { Loading } from "./components/UI";
import Home from "./pages/Home";
import { Movies, MovieDetail } from "./pages/Movies";
import { Showtimes } from "./pages/Showtimes";
import { Seats, Checkout, BookingSuccess, MyTickets } from "./pages/Booking";
import { AuthPage, ForgotPassword, Profile, Favorites } from "./pages/Account";
import {
  Cinemas,
  CinemaDetail,
  Offers,
  About,
  Contact,
  FAQ,
  Legal,
  NotFound,
} from "./pages/Information";
const Admin = lazy(() => import("./pages/Admin"));
export default function App() {
  const location = useLocation();
  useEffect(() => {
    document.title = `${location.pathname.startsWith("/movies") ? "Филми" : location.pathname.startsWith("/booking") ? "Твоят билет" : location.pathname === "/admin" ? "Администрация" : "Твоето място е в киното"} · Пуканков`;
    if (!location.hash) window.scrollTo(0, 0);
    else {
      const timer = setTimeout(
        () =>
          document
            .getElementById(location.hash.slice(1))
            ?.scrollIntoView({ behavior: "smooth" }),
        350,
      );
      return () => clearTimeout(timer);
    }
  }, [location.pathname, location.hash]);
  return (
    <>
      <a className="skip-link" href="#main-content">
        Към съдържанието
      </a>
      <Header />
      <main id="main-content">
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/movies" element={<Movies />} />
            <Route path="/movies/:slug" element={<MovieDetail />} />
            <Route path="/showtimes" element={<Showtimes />} />
            <Route path="/booking/:showtimeId/seats" element={<Seats />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route
              path="/booking/success/:bookingId"
              element={<BookingSuccess />}
            />
            <Route path="/my-tickets" element={<MyTickets />} />
            <Route path="/favorites" element={<Favorites />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/login" element={<AuthPage />} />
            <Route path="/register" element={<AuthPage register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/cinemas" element={<Cinemas />} />
            <Route path="/cinemas/:slug" element={<CinemaDetail />} />
            <Route path="/offers" element={<Offers />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/faq" element={<FAQ />} />
            <Route path="/terms" element={<Legal />} />
            <Route path="/privacy" element={<Legal privacy />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/403" element={<NotFound forbidden />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>
      {!location.pathname.startsWith("/admin") && <Footer />}
    </>
  );
}
