import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import Image from "next/image";

interface Product {
  id: number;
  name: string;
  price: number;
  imageUrl: string;
}

async function getProducts(): Promise<Product[]> {
  try {
    const res = await fetch('http://localhost:8000/api/products', { cache: 'no-store' });
    if (!res.ok) {
      throw new Error('Failed to fetch products');
    }
    return res.json();
  } catch (error) {
    console.error(error);
    // Return an empty array or handle the error as needed
    return [];
  }
}

export default async function Home() {
  const products = await getProducts();

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Our Products</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map((product) => (
          <Card key={product.id}>
            <CardHeader>
              <CardTitle>{product.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative w-full h-48">
                <Image
                  src={product.imageUrl}
                  alt={product.name}
                  fill
                  className="rounded-md object-cover"
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <p className="text-lg font-semibold">${product.price.toFixed(2)}</p>
              {/* Add to cart button can be added here */}
            </CardFooter>
          </Card>
        ))}
      </div>
    </main>
  );
}