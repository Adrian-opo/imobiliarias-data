import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-gray-50">
      <div className="container-page py-12">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white text-xs font-bold">
                JP
              </div>
              <span className="text-base font-bold text-gray-900">
                Imóveis Ji-Paraná
              </span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed">
              Central de imóveis de Ji-Paraná - RO. Reunimos ofertas de
              diversas imobiliárias em um só lugar para facilitar sua busca.
            </p>
          </div>

          {/* Navegação */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Navegação
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Início
                </Link>
              </li>
              <li>
                <Link
                  href="/imoveis"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Imóveis
                </Link>
              </li>
              <li>
                <Link
                  href="/novos"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Novos
                </Link>
              </li>
              <li>
                <Link
                  href="/como-funciona"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Como funciona
                </Link>
              </li>
            </ul>
          </div>

          {/* Imóveis */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Imóveis
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/imoveis?purpose=venda"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Comprar
                </Link>
              </li>
              <li>
                <Link
                  href="/imoveis?purpose=aluguel"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Alugar
                </Link>
              </li>
              <li>
                <Link
                  href="/novos"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Imóveis novos
                </Link>
              </li>
            </ul>
          </div>

          {/* Info */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              Informações
            </h3>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/como-funciona"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Como funciona
                </Link>
              </li>
              <li className="text-sm text-gray-500">
                Ji-Paraná, Rondônia
              </li>
              <li className="text-sm text-gray-500">
                Dados atualizados 2x ao dia
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-gray-200 pt-6 text-center">
          <p className="text-xs text-gray-400">
            &copy; {new Date().getFullYear()} Imóveis Ji-Paraná. Este site é
            um agregador de imóveis e não substitui o site oficial das
            imobiliárias. Preços e disponibilidade sujeitos a alterações.
          </p>
        </div>
      </div>
    </footer>
  );
}
